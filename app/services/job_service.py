import json
import random
import sqlite3
import threading
import time
from datetime import datetime
from typing import List, Optional

from app import config
from app.services.email_service import build_message
from app.services.sender_service import get_sender
from app.services import whatsapp_service


def get_whatsapp_sender():
    return whatsapp_service.WhatsAppSender()


_running: set[int] = set()
_running_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT 'email',
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    cc TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT
);
CREATE TABLE IF NOT EXISTS job_recipients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    error TEXT,
    sent_at TEXT
);
CREATE TABLE IF NOT EXISTS job_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL REFERENCES jobs(id),
    filename TEXT NOT NULL,
    content BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_recipients_job ON job_recipients(job_id, status);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _db() as conn:
        conn.executescript(SCHEMA)
        # Upgrade databases created before WhatsApp support was added.
        job_cols = [r["name"] for r in conn.execute("PRAGMA table_info(jobs)")]
        if "channel" not in job_cols:
            conn.execute("ALTER TABLE jobs ADD COLUMN channel TEXT NOT NULL DEFAULT 'email'")
        recipient_cols = [r["name"] for r in conn.execute("PRAGMA table_info(job_recipients)")]
        if "email" in recipient_cols:
            conn.execute("ALTER TABLE job_recipients RENAME COLUMN email TO address")


def create_job(subject: str, body: str, cc: List[str], recipients: List[str],
               attachments: List[tuple[str, bytes]], channel: str = "email") -> int:
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (created_at, channel, subject, body, cc) VALUES (?, ?, ?, ?, ?)",
            (_now(), channel, subject, body, json.dumps(cc)),
        )
        job_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO job_recipients (job_id, address) VALUES (?, ?)",
            [(job_id, address) for address in recipients],
        )
        conn.executemany(
            "INSERT INTO job_attachments (job_id, filename, content) VALUES (?, ?, ?)",
            [(job_id, name, content) for name, content in attachments],
        )
    return job_id


def _counts(conn: sqlite3.Connection, job_id: int) -> dict:
    rows = conn.execute(
        "SELECT status, COUNT(*) AS n FROM job_recipients WHERE job_id = ? GROUP BY status", (job_id,)
    ).fetchall()
    counts = {"pending": 0, "sent": 0, "failed": 0}
    counts.update({r["status"]: r["n"] for r in rows})
    counts["total"] = sum(counts.values())
    return counts


def get_job(job_id: int, include_recipients: bool = True) -> Optional[dict]:
    with _db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            return None
        result = dict(job)
        result["cc"] = json.loads(result["cc"])
        result["counts"] = _counts(conn, job_id)
        result["attachments"] = [r["filename"] for r in conn.execute(
            "SELECT filename FROM job_attachments WHERE job_id = ? ORDER BY id", (job_id,))]
        if include_recipients:
            result["recipients"] = [dict(r) for r in conn.execute(
                "SELECT address, status, error, sent_at FROM job_recipients WHERE job_id = ? ORDER BY id",
                (job_id,))]
    return result


def list_jobs(limit: int = 20) -> List[dict]:
    with _db() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM jobs ORDER BY id DESC LIMIT ?", (limit,))]
    return [get_job(i, include_recipients=False) for i in ids]


def _set_status(job_id: int, status: str, error: Optional[str] = None) -> None:
    with _db() as conn:
        conn.execute("UPDATE jobs SET status = ?, error = ? WHERE id = ?", (status, error, job_id))


def start_job(job_id: int) -> None:
    """Starts sending in a background thread (no-op if this job is already running)."""
    with _running_lock:
        if job_id in _running:
            return
        _running.add(job_id)
    _set_status(job_id, "running")
    threading.Thread(target=_run_job, args=(job_id,), daemon=True).start()


def cancel_job(job_id: int) -> None:
    _set_status(job_id, "cancelled")


def retry_failed(job_id: int) -> None:
    with _db() as conn:
        conn.execute(
            "UPDATE job_recipients SET status = 'pending', error = NULL WHERE job_id = ? AND status = 'failed'",
            (job_id,),
        )
    start_job(job_id)


def resume_unfinished() -> None:
    """Called on startup: continues jobs that were interrupted by a restart."""
    with _db() as conn:
        ids = [r["id"] for r in conn.execute("SELECT id FROM jobs WHERE status = 'running'")]
    for job_id in ids:
        start_job(job_id)


def _whatsapp_sent_today(conn: sqlite3.Connection) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM job_recipients r JOIN jobs j ON j.id = r.job_id "
        "WHERE j.channel = 'whatsapp' AND r.status = 'sent' AND r.sent_at >= ?",
        (datetime.now().date().isoformat(),),
    ).fetchone()[0]


def _run_job(job_id: int) -> None:
    lock = None
    try:
        with _db() as conn:
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            attachments = [(r["filename"], r["content"]) for r in conn.execute(
                "SELECT filename, content FROM job_attachments WHERE job_id = ? ORDER BY id", (job_id,))]
        whatsapp = job["channel"] == "whatsapp"

        if whatsapp:
            # Only one browser can use the WhatsApp login at a time; later jobs wait their turn.
            lock = whatsapp_service.browser_lock
            lock.acquire()
            sender = get_whatsapp_sender()

            def deliver(address: str) -> None:
                sender.send(address, job["body"], attachments)

            def pause() -> float:
                return random.uniform(config.WA_MIN_DELAY_SECONDS, config.WA_MAX_DELAY_SECONDS)
        else:
            sender = get_sender()
            if sender is None:
                _set_status(job_id, "error", "No sending account configured. See README.")
                return
            cc = json.loads(job["cc"])

            def deliver(address: str) -> None:
                sender.send(build_message(address, job["subject"], job["body"], cc, attachments,
                                          sender.from_email, config.FROM_NAME or None))

            def pause() -> float:
                return config.SEND_DELAY_SECONDS

        with sender:
            first = True
            while True:
                with _db() as conn:
                    row = conn.execute(
                        "SELECT id, address FROM job_recipients WHERE job_id = ? AND status = 'pending' ORDER BY id LIMIT 1",
                        (job_id,),
                    ).fetchone()
                    over_limit = whatsapp and _whatsapp_sent_today(conn) >= config.WA_DAILY_LIMIT
                if row is None:
                    break
                if over_limit:
                    _set_status(job_id, "error", f"Daily WhatsApp limit of {config.WA_DAILY_LIMIT} reached. "
                                                 "Click Resume tomorrow to continue.")
                    return
                if not first:
                    time.sleep(pause())
                first = False
                with _db() as conn:
                    if conn.execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()[0] == "cancelled":
                        return

                try:
                    deliver(row["address"])
                    status, error = "sent", None
                except Exception as e:  # record the failure and move on to the next recipient
                    status, error = "failed", str(e)[:500]
                with _db() as conn:
                    conn.execute(
                        "UPDATE job_recipients SET status = ?, error = ?, sent_at = ? WHERE id = ?",
                        (status, error, _now(), row["id"]),
                    )
        _set_status(job_id, "completed")
    except Exception as e:  # login / connection failure: remaining recipients stay pending
        _set_status(job_id, "error", str(e)[:500])
    finally:
        if lock:
            lock.release()
        with _running_lock:
            _running.discard(job_id)
