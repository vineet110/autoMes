import pytest

from app.services.email_service import build_message
from app.services.sender_service import RecipientRefused, SmtpSender


class FakeConnection:
    def __init__(self, refused):
        self.refused = refused

    def send_message(self, message):
        return self.refused


def test_refused_recipient_is_a_failure_even_if_cc_was_accepted():
    sender = SmtpSender()
    sender._conn = FakeConnection({"gone@example.com": (550, b"5.1.1 Mailbox not found")})
    message = build_message("gone@example.com", "S", "B", ["boss@example.com"])
    with pytest.raises(RecipientRefused, match="550 5.1.1 Mailbox not found"):
        sender.send(message)


def test_refused_cc_only_still_counts_as_sent():
    sender = SmtpSender()
    sender._conn = FakeConnection({"boss@example.com": (550, b"no such user")})
    sender.send(build_message("client@example.com", "S", "B", ["boss@example.com"]))


def test_wrong_password_gives_clear_message(monkeypatch):
    import smtplib

    from app import config

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def starttls(self, context=None):
            pass

        def login(self, user, password):
            raise smtplib.SMTPAuthenticationError(535, b"5.7.8 Username and Password not accepted")

        def close(self):
            self.closed = True

    monkeypatch.setattr(config, "SMTP_PORT", 587)
    monkeypatch.setattr(config, "SMTP_USER", "me@example.com")
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    with pytest.raises(RuntimeError, match="App Password"):
        SmtpSender().__enter__()
