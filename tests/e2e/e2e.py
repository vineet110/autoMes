"""
End-to-end test: real app + real browser UI (Chrome) + real SMTP (STARTTLS + login) + fake WhatsApp Web.

    pip install aiosmtpd
    cd frontend && npm run build && cd ..
    python tests/e2e/e2e.py            # all flows
    python tests/e2e/e2e.py email_flow # one flow

Nothing is sent to real people: mail goes to a local test server, WhatsApp to a local imitation page.
"""
import email
import email.policy
import io
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

import docx
from playwright.sync_api import expect, sync_playwright

HERE = Path(__file__).parent
APP = HERE.parents[1]
sys.path.insert(0, str(APP))
from tests.test_file_extraction import make_pdf  # noqa: E402

APP_PORT, SMTP_PORT, WA_PORT = 8790, 8587, 8599
BASE = f"http://127.0.0.1:{APP_PORT}"
MAIL = HERE / "mail"
FILES = HERE / "files"
results = []
procs = {}


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f"  -- {detail}" if detail and not cond else ""), flush=True)


def wait_http(url, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    raise RuntimeError(f"{url} did not come up")


def start_app(password="apppassword", delay="0.3", smtp_port=SMTP_PORT):
    env = {**os.environ,
           "SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(smtp_port), "SMTP_USER": "me@kjs-e2e.com",
           "SMTP_PASSWORD": password, "FROM_NAME": "KJS Sales", "SEND_DELAY_SECONDS": delay,
           "SSL_CERT_FILE": str(HERE / "cert.pem"), "DB_PATH": str(HERE / "e2e.db"),
           "FAKE_WA_URL": f"http://127.0.0.1:{WA_PORT}",
           "WA_MIN_DELAY_SECONDS": "0.5", "WA_MAX_DELAY_SECONDS": "1"}
    procs["app"] = subprocess.Popen([sys.executable, str(HERE / "run_app.py"), str(APP_PORT)], env=env,
                                    stdout=open(HERE / "app.log", "a"), stderr=subprocess.STDOUT)
    wait_http(BASE + "/api/status")


def stop_app():
    p = procs.pop("app", None)
    if p:
        p.kill()
        p.wait()


def mails():
    out = []
    for f in sorted(MAIL.glob("*.json")):
        m = json.loads(f.read_text())
        m["msg"] = email.message_from_string(m["data"], policy=email.policy.default)
        out.append(m)
    return out


def api(path, data=None):
    req = urllib.request.Request(BASE + path, data=data, method="POST" if data is not None else "GET")
    return json.loads(urllib.request.urlopen(req).read())


def wait_job(job_id, statuses=("completed", "error", "cancelled"), timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        job = api(f"/api/jobs/{job_id}")
        if job["status"] in statuses:
            return job
        time.sleep(0.5)
    raise RuntimeError(f"job {job_id} stuck: {job['status']} {job['counts']}")


def make_files():
    FILES.mkdir(exist_ok=True)
    (FILES / "clients.csv").write_text(
        "Name,Email,City\nAsha,asha@client-e2e.com,Pune\nRavi,RAVI@client-e2e.com,Delhi\nDup,asha@client-e2e.com,Pune\n"
        "Bad,not-an-email,Goa\nReject,reject@client-e2e.com,Mumbai\n", encoding="utf-8")
    (FILES / "dealers.pdf").write_bytes(make_pdf("Dealers: dealer1@dealer-e2e.com, dealer2@dealer-e2e.com"))
    d = docx.Document()
    d.add_paragraph("Contact: priya@partner-e2e.com")
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Kiran", "kiran@partner-e2e.com"
    d.save(FILES / "partners.docx")
    (FILES / "PriceList.pdf").write_bytes(make_pdf("Price list"))
    (FILES / "logo.png").write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d4944415478da63f8cf"
        "c0f01f0005000201a5f6e0a80000000049454e44ae426082"))
    (FILES / "phones.csv").write_text("name,mobile\nA,98765 43210\nB,+91 0000000000\n", encoding="utf-8")


def email_flow(page):
    page.goto(BASE + "/connections/")
    expect(page.get_by_text("SMTP (127.0.0.1) as me@kjs-e2e.com")).to_be_visible()
    check("connections page shows SMTP account", True)

    page.goto(BASE + "/")
    page.set_input_files("input[accept='.csv,.pdf,.docx,.txt']",
                         [str(FILES / "clients.csv"), str(FILES / "dealers.pdf"), str(FILES / "partners.docx")])
    expect(page.get_by_text("Added 7 new addresses")).to_be_visible()
    check("upload CSV+PDF+DOCX -> 7 unique valid addresses", True)
    expect(page.get_by_text("1 skipped")).to_be_visible()
    check("invalid CSV row reported as skipped", True)

    page.fill("input[placeholder='Type or paste addresses']", "manual@client-e2e.com, asha@client-e2e.com")
    page.get_by_role("button", name="Add").click()
    expect(page.get_by_text("8 recipients")).to_be_visible()
    check("manual add (with duplicate) -> 8 recipients", True)

    subject = "Diwali ऑफ़र ✨ special prices"
    body = "Dear Sir/Madam,\n\nPlease find our latest price list attached.\n\nRegards,\nVineet"
    page.fill("#subject", subject)
    page.fill("#body", body)
    page.fill("#cc", "boss@kjs-e2e.com")
    page.set_input_files("input[type=file]:not([accept])", [str(FILES / "PriceList.pdf"), str(FILES / "logo.png")])
    expect(page.get_by_text("2 · ")).to_be_visible()

    page.fill("input[placeholder='you@company.com']", "tester@kjs-e2e.com")
    page.get_by_role("button", name="Send test").click()
    expect(page.get_by_text("Test sent to tester@kjs-e2e.com")).to_be_visible(timeout=20000)
    m = mails()[-1]
    check("test email delivered without CC", m["rcpt_tos"] == ["tester@kjs-e2e.com"] and m["msg"]["Cc"] is None, m["rcpt_tos"])

    before = len(mails())
    page.get_by_role("button", name="Review & send").click()
    expect(page.get_by_role("heading", name="Send 8 emails?")).to_be_visible()
    page.get_by_role("button", name="Send now").click()
    page.wait_for_url("**/campaigns/view/?id=*")
    job_id = int(page.url.split("id=")[1])
    expect(page.get_by_text("Completed", exact=True)).to_be_visible(timeout=60000)
    job = api(f"/api/jobs/{job_id}")
    check("campaign completed: 7 sent, 1 failed", job["counts"] == {"pending": 0, "sent": 7, "failed": 1, "total": 8}, job["counts"])
    failed = [r for r in job["recipients"] if r["status"] == "failed"]
    check("rejected address failed with SMTP reason", failed and "Mailbox not found" in (failed[0]["error"] or ""), failed)
    expect(page.get_by_text("Mailbox not found").locator("visible=true").first).to_be_visible()
    check("failure reason visible in UI", True)

    # The server took the CC copy of the rejected message before refusing the recipient,
    # so only the 7 accepted recipients count as delivered.
    sent = [m for m in mails()[before:] if m["msg"]["To"] in m["rcpt_tos"]]
    check("7 messages reached their recipients", len(sent) == 7, len(sent))
    ok = True
    for m in sent:
        msg = m["msg"]
        to = msg["To"]
        ok &= "," not in to
        ok &= set(m["rcpt_tos"]) == {to, "boss@kjs-e2e.com"}
        ok &= msg["Cc"] == "boss@kjs-e2e.com"
        ok &= msg["From"] == "KJS Sales <me@kjs-e2e.com>"
        ok &= str(msg["Subject"]) == subject
        ok &= m["tls"] and m["authenticated"]
        names = [p.get_filename() for p in msg.iter_attachments()]
        ok &= names == ["PriceList.pdf", "logo.png"]
        ok &= msg.get_body(("plain",)).get_content().replace("\r\n", "\n").strip() == body
    check("each email: one To, CC, From name, unicode subject, body, 2 attachments, TLS+auth", ok,
          [(m["msg"]["To"], m["rcpt_tos"]) for m in sent])

    page.get_by_role("button", name="Retry 1 failed").click()
    expect(page.get_by_text("Completed", exact=True)).to_be_visible(timeout=30000)
    page.wait_for_timeout(1500)
    job = api(f"/api/jobs/{job_id}")
    after = mails()
    check("retry re-attempts only the failed one", job["counts"]["sent"] == 7 and job["counts"]["failed"] == 1
          and len(after) == before + 9 and after[-1]["msg"]["To"] == "reject@client-e2e.com", job["counts"])

    page.goto(BASE + "/campaigns/")
    expect(page.get_by_text(subject)).to_be_visible()
    check("campaign listed on Campaigns page", True)
    return job_id


def stop_resume_flow(page):
    form = urllib.parse.urlencode({"recipients": "\n".join(f"bulk{i}@client-e2e.com" for i in range(25)),
                                   "subject": "Stop test", "body": "x"}).encode()
    job_id = api("/api/jobs", form)["job_id"]
    page.goto(f"{BASE}/campaigns/view/?id={job_id}")
    page.wait_for_timeout(1500)
    page.get_by_role("button", name="Stop").click()
    job = wait_job(job_id, ("cancelled",), 10)
    page.wait_for_timeout(1500)
    job = api(f"/api/jobs/{job_id}")
    check("Stop halts sending", job["status"] == "cancelled" and job["counts"]["pending"] > 0, job["counts"])
    page.reload()
    page.get_by_role("button", name="Resume").click()
    job = wait_job(job_id, ("completed",), 60)
    check("Resume finishes the rest", job["counts"]["sent"] == 25, job["counts"])

    # Restart the server in the middle of a job: it must continue by itself.
    form = urllib.parse.urlencode({"recipients": "\n".join(f"restart{i}@client-e2e.com" for i in range(20)),
                                   "subject": "Restart test", "body": "x"}).encode()
    job_id = api("/api/jobs", form)["job_id"]
    time.sleep(2)
    stop_app()
    mid = len([m for m in mails() if m["msg"]["Subject"] == "Restart test"])
    start_app()
    job = wait_job(job_id, ("completed",), 60)
    got = [m["msg"]["To"] for m in mails() if m["msg"]["Subject"] == "Restart test"]
    check("job resumes after app restart", job["counts"]["sent"] == 20, f"{job['counts']} (sent before kill: {mid})")
    check("no recipient lost after restart", set(got) == {f"restart{i}@client-e2e.com" for i in range(20)},
          f"{len(got)} delivered, {len(set(got))} unique")


def whatsapp_flow(page):
    page.goto(BASE + "/connections/")
    page.get_by_role("button", name="Connect WhatsApp").click()
    expect(page.get_by_text("Connected", exact=True)).to_be_visible(timeout=60000)
    check("Connect WhatsApp -> Connected", True)

    page.goto(BASE + "/")
    page.get_by_role("button", name="WhatsApp").click()
    page.set_input_files("input[accept='.csv,.pdf,.docx,.txt']", [str(FILES / "phones.csv")])
    expect(page.get_by_text("Added 2 new numbers")).to_be_visible()
    check("phone CSV upload -> 2 numbers", True)
    body = "Namaste! 🙏\nNew stock arrived.\nCall us: +91 98765 43210 & visit https://kjs.example/?a=1&b=2"
    page.fill("#body", body)
    page.set_input_files("input[type=file]:not([accept])", [str(FILES / "PriceList.pdf")])
    page.get_by_role("button", name="Review & send").click()
    page.get_by_role("button", name="Send now").click()
    page.wait_for_url("**/campaigns/view/?id=*")
    job_id = int(page.url.split("id=")[1])
    job = wait_job(job_id, timeout=120)
    check("WhatsApp campaign completed: 1 sent, 1 failed", job["status"] == "completed" and
          job["counts"]["sent"] == 1 and job["counts"]["failed"] == 1, (job["status"], job["error"], job["recipients"]))
    log = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{WA_PORT}/log").read())
    texts = [e for e in log if e["kind"] == "text"]
    files = [e for e in log if e["kind"] == "file"]
    check("WhatsApp text arrived exactly (emoji, new lines, & ?)", len(texts) == 1 and texts[0]["phone"] == "919876543210"
          and texts[0]["text"].strip() == body, texts)
    check("WhatsApp attachment sent", len(files) == 1 and files[0]["name"] == "PriceList.pdf", files)
    bad = [r for r in job["recipients"] if r["status"] == "failed"]
    check("number not on WhatsApp marked failed", bad and "not on WhatsApp" in bad[0]["error"], bad)


def wrong_password_flow(page):
    stop_app()
    start_app(smtp_port=1)  # nothing listens there: mail server unreachable
    print("   listeners:", subprocess.run("netstat -ano | findstr LISTENING | findstr :%d" % APP_PORT, shell=True,
                                        capture_output=True, text=True).stdout.strip(), "new pid", procs["app"].pid)
    try:
        page.goto(BASE + "/", timeout=10000)
    except Exception as ex:
        print("   same page goto failed:", str(ex).splitlines()[0], "| url was", page.url)
        page.screenshot(path=str(HERE / "hang.png"))
        page = page.context.new_page()
        page.goto(BASE + "/", timeout=10000)
        print("   new page goto OK")
    page.fill("#subject", "x")
    page.fill("#body", "y")
    page.fill("input[placeholder='you@company.com']", "tester@kjs-e2e.com")
    page.get_by_role("button", name="Send test").click()
    # The app must stay responsive while the send is in progress.
    t = time.time()
    urllib.request.urlopen(BASE + "/api/status", timeout=5)
    check("app stays responsive during a test send", time.time() - t < 2)
    err = page.get_by_text("Sending failed")
    expect(err).to_be_visible(timeout=20000)
    check("unreachable mail server -> readable error on Send test", "Could not connect to the mail server" in err.inner_text(), err.inner_text())
    print("   message shown:", err.inner_text()[:150])
    stop_app()
    start_app()


def main():
    for d in (MAIL, HERE / "wa_profile"):
        shutil.rmtree(d, ignore_errors=True)
    MAIL.mkdir()
    for f in ("e2e.db", "app.log"):
        (HERE / f).unlink(missing_ok=True)
    make_files()
    procs["smtp"] = subprocess.Popen([sys.executable, str(HERE / "smtp_server.py"), str(SMTP_PORT)],
                                     stdout=open(HERE / "smtp.log", "w"), stderr=subprocess.STDOUT)
    procs["wa"] = subprocess.Popen([sys.executable, str(HERE / "fake_whatsapp.py"), str(WA_PORT)],
                                   stdout=open(HERE / "wa.log", "w"), stderr=subprocess.STDOUT)
    time.sleep(3)
    wait_http(f"http://127.0.0.1:{WA_PORT}/log")
    start_app()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            page = browser.new_page(viewport={"width": 1400, "height": 1000})
            js_errors = []
            page.on("pageerror", lambda e: js_errors.append(str(e)))
            page.on("console", lambda m: m.type == "error" and js_errors.append(m.text))
            flows = [globals()[n] for n in sys.argv[1:]] or [email_flow, stop_resume_flow, whatsapp_flow, wrong_password_flow]
            for flow in flows:
                try:
                    flow(page)
                except Exception as e:
                    check(f"{flow.__name__} ran without crashing", False, f"{e}\n{traceback.format_exc()[-800:]}")
                    page.screenshot(path=str(HERE / f"fail_{flow.__name__}.png"), full_page=True)
            page.goto(BASE + "/classic")
            expect(page.get_by_role("heading", name="Auto Mailer")).to_be_visible()
            check("classic UI still loads", True)
            # The deliberate failed test send answers 502, which the browser logs; anything else is a bug.
            js_errors = [e for e in js_errors if "502" not in e and "ERR_CONNECTION_REFUSED" not in e]  # restarts are deliberate
            check("no JavaScript errors in browser", not js_errors, js_errors[:5])
            browser.close()
    finally:
        stop_app()
        for p_ in procs.values():
            p_.kill()
    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    import urllib.parse  # noqa: F401
    main()
