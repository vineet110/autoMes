import os
import threading
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from app import config
from app.services import job_service, whatsapp_service
from app.services.email_service import build_message
from app.services.recipient_service import extract_recipients, parse_email_list, parse_phone_list
from app.services.sender_service import get_sender

STATIC_DIR = config.BASE_DIR / "static"  # original plain-HTML UI, kept at /classic
FRONTEND_DIR = config.BASE_DIR / "frontend" / "out"  # Next.js build (npm run build)


@asynccontextmanager
async def lifespan(app: FastAPI):
    job_service.init_db()
    job_service.resume_unfinished()
    yield


app = FastAPI(title="Auto Mailer", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
# Lets the Next.js dev server (npm run dev) call the API from another port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/classic")
def classic_index():
    return FileResponse(STATIC_DIR / "index.html")


if not FRONTEND_DIR.exists():
    # Fall back to the classic UI until the Next.js frontend has been built.
    app.get("/")(classic_index)


@app.get("/api/status")
def status():
    sender = get_sender()
    return {"configured": sender is not None, "sender": sender.label if sender else None}


@app.post("/api/recipients/parse")
async def parse_recipients(files: List[UploadFile] = File(...), channel: str = Form("email")):
    emails: List[str] = []
    seen: set[str] = set()
    problems: List[str] = []
    per_file = []
    for upload in files:
        try:
            # Parsing a big PDF is slow; run it off the event loop so the app stays responsive.
            found, issues = await run_in_threadpool(extract_recipients, upload.filename, await upload.read(), channel)
        except ValueError as e:
            problems.append(str(e))
            per_file.append({"file": upload.filename, "found": 0})
            continue
        problems.extend(f"{upload.filename} - {issue}" for issue in issues)
        per_file.append({"file": upload.filename, "found": len(found)})
        for email in found:
            if email.lower() not in seen:
                seen.add(email.lower())
                emails.append(email)
    return {"emails": emails, "problems": problems, "files": per_file}


async def _read_attachments(attachments: List[UploadFile]) -> List[tuple[str, bytes]]:
    result = [(a.filename, await a.read()) for a in attachments if a.filename]
    total_mb = sum(len(content) for _, content in result) / (1024 * 1024)
    if total_mb > config.MAX_ATTACHMENT_MB:
        raise HTTPException(400, f"Attachments total {total_mb:.1f} MB; the limit is {config.MAX_ATTACHMENT_MB:g} MB.")
    return result


def _validate_compose(subject: str, body: str, cc: str) -> List[str]:
    if not subject.strip():
        raise HTTPException(400, "Subject is required.")
    if not body.strip():
        raise HTTPException(400, "Message body is required.")
    cc_list, cc_invalid = parse_email_list(cc)
    if cc_invalid:
        raise HTTPException(400, "Invalid CC address: " + "; ".join(cc_invalid))
    return cc_list


def _send_one(sender, message) -> None:
    # Blocking network call: always run it through run_in_threadpool, never on the event loop.
    with sender:
        sender.send(message)


@app.post("/api/send-test")
async def send_test(
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    cc: str = Form(""),
    attachments: List[UploadFile] = File(default=[]),
):
    """Sends one copy to the given address (without CC) so the user can check how it looks."""
    _validate_compose(subject, body, cc)
    to_list, invalid = parse_email_list(to)
    if invalid or len(to_list) != 1:
        raise HTTPException(400, "Enter one valid test address.")
    sender = get_sender()
    if sender is None:
        raise HTTPException(400, "No sending account configured. See README.")
    files = await _read_attachments(attachments)
    try:
        await run_in_threadpool(_send_one, sender, build_message(
            to_list[0], subject, body, None, files, sender.from_email, config.FROM_NAME or None))
    except Exception as e:
        raise HTTPException(502, f"Sending failed: {e}")
    return {"ok": True}


@app.post("/api/jobs")
async def create_job(
    recipients: str = Form(...),
    subject: str = Form(""),
    body: str = Form(...),
    cc: str = Form(""),
    channel: str = Form("email"),
    attachments: List[UploadFile] = File(default=[]),
):
    if channel == "whatsapp":
        if not body.strip() and not any(a.filename for a in attachments):
            raise HTTPException(400, "Write a message or add an attachment.")
        cc_list = []
        to_list, invalid = parse_phone_list(recipients)
        # The subject is not sent on WhatsApp; it only names the job in the history.
        subject = subject.strip() or (body.strip().splitlines() or ["WhatsApp message"])[0][:60]
    else:
        cc_list = _validate_compose(subject, body, cc)
        to_list, invalid = parse_email_list(recipients)
        if get_sender() is None:
            raise HTTPException(400, "No sending account configured. See README.")
    if invalid:
        raise HTTPException(400, "Invalid recipient: " + "; ".join(invalid[:10]))
    if not to_list:
        raise HTTPException(400, "Add at least one recipient.")
    files = await _read_attachments(attachments)
    job_id = job_service.create_job(subject, body, cc_list, to_list, files, channel)
    job_service.start_job(job_id)
    return {"job_id": job_id}


@app.get("/api/jobs")
def list_jobs():
    return job_service.list_jobs()


def _job_or_404(job_id: int) -> dict:
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@app.get("/api/jobs/{job_id}")
def get_job(job_id: int):
    return _job_or_404(job_id)


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: int):
    _job_or_404(job_id)
    job_service.retry_failed(job_id)
    return {"ok": True}


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: int):
    _job_or_404(job_id)
    job_service.cancel_job(job_id)
    return {"ok": True}


@app.get("/api/whatsapp/status")
def whatsapp_status():
    return {
        **whatsapp_service.login_state(),
        "daily_limit": config.WA_DAILY_LIMIT,
        "delay": [config.WA_MIN_DELAY_SECONDS, config.WA_MAX_DELAY_SECONDS],
    }


@app.post("/api/whatsapp/login")
def whatsapp_login():
    """Opens a browser window with WhatsApp Web so the user can scan the QR code."""
    threading.Thread(target=whatsapp_service.login, daemon=True).start()
    return {"ok": True}


class NextStaticFiles(StaticFiles):
    """
    Static export writes route prefetch data as `__next.campaigns/__PAGE__.txt`, but the
    browser requests it as `__next.campaigns.__PAGE__.txt`; map one to the other.
    """

    def lookup_path(self, path):
        full_path, stat = super().lookup_path(path)
        folder, name = os.path.split(path)
        if stat is None and name.startswith("__next.") and name.endswith(".txt"):
            segments = name[len("__next."):-len(".txt")].split(".")
            return super().lookup_path(os.path.join(folder, "__next." + "/".join(segments) + ".txt"))
        return full_path, stat


# Must stay last: serves the built Next.js pages for every path the API doesn't handle.
if FRONTEND_DIR.exists():
    app.mount("/", NextStaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
