import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.services import job_service


class FakeSender:
    def __init__(self, fail_for=()):
        self.from_email = "me@example.com"
        self.label = "Fake"
        self.fail_for = set(fail_for)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def send(self, message):
        if message["To"] in self.fail_for:
            raise RuntimeError("mailbox unavailable")
        self.sent.append(message)


class FakeWhatsAppSender:
    def __init__(self, fail_for=()):
        self.fail_for = set(fail_for)
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def send(self, phone, text, attachments=None):
        if phone in self.fail_for:
            raise RuntimeError("This number is not on WhatsApp.")
        self.sent.append((phone, text, [name for name, _ in attachments or []]))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "SEND_DELAY_SECONDS", 0)
    monkeypatch.setattr(config, "WA_MIN_DELAY_SECONDS", 0)
    monkeypatch.setattr(config, "WA_MAX_DELAY_SECONDS", 0)
    sender = FakeSender(fail_for={"bad@example.com"})
    import app.main as main
    monkeypatch.setattr(job_service, "get_sender", lambda: sender)
    monkeypatch.setattr(main, "get_sender", lambda: sender)
    wa_sender = FakeWhatsAppSender(fail_for={"+919999999999"})
    monkeypatch.setattr(job_service, "get_whatsapp_sender", lambda: wa_sender)
    with TestClient(main.app) as c:
        c.sender = sender
        c.wa_sender = wa_sender
        yield c


def wait_for_job(client, job_id):
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] != "running":
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_full_send_flow(client):
    files = [("files", ("people.txt", b"one@example.com two@example.com bad@example.com", "text/plain"))]
    parsed = client.post("/api/recipients/parse", files=files).json()
    assert parsed["emails"] == ["one@example.com", "two@example.com", "bad@example.com"]

    res = client.post(
        "/api/jobs",
        data={"recipients": "\n".join(parsed["emails"]), "subject": "Hi", "body": "Hello", "cc": "boss@example.com"},
        files=[("attachments", ("note.txt", b"attached", "text/plain"))],
    )
    assert res.status_code == 200, res.text
    job = wait_for_job(client, res.json()["job_id"])

    assert job["status"] == "completed"
    assert job["counts"] == {"pending": 0, "sent": 2, "failed": 1, "total": 3}
    assert job["attachments"] == ["note.txt"]

    # Each message goes to exactly one recipient, with the common CC.
    assert [m["To"] for m in client.sender.sent] == ["one@example.com", "two@example.com"]
    assert all(m["Cc"] == "boss@example.com" for m in client.sender.sent)
    assert all(m["From"] == "me@example.com" for m in client.sender.sent)

    # Retrying only resends the failed one.
    client.sender.fail_for.clear()
    client.post(f"/api/jobs/{job['id']}/retry")
    job = wait_for_job(client, job["id"])
    assert job["counts"]["sent"] == 3
    assert [m["To"] for m in client.sender.sent][-1] == "bad@example.com"


def test_rejects_invalid_input(client):
    res = client.post("/api/jobs", data={"recipients": "nope", "subject": "Hi", "body": "Hello"})
    assert res.status_code == 400
    res = client.post("/api/jobs", data={"recipients": "a@example.com", "subject": " ", "body": "Hello"})
    assert res.status_code == 400


def test_send_test_email(client):
    res = client.post("/api/send-test", data={"to": "me@example.com", "subject": "S", "body": "B", "cc": "x@example.com"})
    assert res.status_code == 200
    assert client.sender.sent[-1]["Cc"] is None


def test_whatsapp_flow(client):
    files = [("files", ("people.csv", b"name,mobile\nA,98765 43210\nB,9999999999\n", "text/csv"))]
    parsed = client.post("/api/recipients/parse", files=files, data={"channel": "whatsapp"}).json()
    assert parsed["emails"] == ["+919876543210", "+919999999999"]

    res = client.post(
        "/api/jobs",
        data={"channel": "whatsapp", "recipients": "\n".join(parsed["emails"]), "body": "Hello there\nSecond line"},
        files=[("attachments", ("price.pdf", b"%PDF", "application/pdf"))],
    )
    assert res.status_code == 200, res.text
    job = wait_for_job(client, res.json()["job_id"])

    assert job["channel"] == "whatsapp"
    assert job["subject"] == "Hello there"
    assert job["counts"] == {"pending": 0, "sent": 1, "failed": 1, "total": 2}
    assert client.wa_sender.sent == [("+919876543210", "Hello there\nSecond line", ["price.pdf"])]
    assert client.sender.sent == []  # nothing went out by email


def test_whatsapp_daily_limit(client, monkeypatch):
    monkeypatch.setattr(config, "WA_DAILY_LIMIT", 1)
    res = client.post("/api/jobs", data={"channel": "whatsapp", "recipients": "9876543210\n9876543211", "body": "Hi"})
    job = wait_for_job(client, res.json()["job_id"])
    assert job["status"] == "error"
    assert "limit" in job["error"]
    assert job["counts"]["sent"] == 1 and job["counts"]["pending"] == 1


