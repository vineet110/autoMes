import base64
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from app import config


class SmtpSender:
    """Sends through any SMTP server (Gmail / Google Workspace with an App Password, Outlook, etc.)."""

    def __init__(self):
        self.from_email = config.SMTP_USER
        self.label = f"SMTP ({config.SMTP_HOST}) as {config.SMTP_USER}"
        self._conn: Optional[smtplib.SMTP] = None

    def _connect(self) -> smtplib.SMTP:
        context = ssl.create_default_context()
        try:
            if config.SMTP_PORT == 465:
                conn = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, context=context, timeout=60)
            else:
                conn = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=60)
                conn.starttls(context=context)
        except OSError as e:  # refused, timed out, DNS failure, TLS problems
            raise RuntimeError(
                f"Could not connect to the mail server {config.SMTP_HOST}:{config.SMTP_PORT}. "
                f"Check SMTP_HOST / SMTP_PORT in .env and your internet connection. ({e})"
            ) from e
        try:
            conn.login(config.SMTP_USER, config.SMTP_PASSWORD)
        except smtplib.SMTPAuthenticationError as e:
            conn.close()
            raise RuntimeError(
                f"Email login failed for {config.SMTP_USER}. Check SMTP_USER and SMTP_PASSWORD in .env "
                f"(Gmail needs an App Password, not your normal password). Server said: {e.smtp_code}"
            ) from e
        return conn

    def __enter__(self):
        self._conn = self._connect()
        return self

    def __exit__(self, *exc):
        if self._conn:
            try:
                self._conn.quit()
            except smtplib.SMTPException:
                pass
            self._conn = None

    def send(self, message: EmailMessage) -> None:
        try:
            refused = self._conn.send_message(message)
        except (smtplib.SMTPServerDisconnected, ConnectionError):
            # Long jobs can outlive the server's idle timeout; reconnect once and retry.
            self._conn = self._connect()
            refused = self._conn.send_message(message)
        # smtplib only raises when *every* recipient is refused. With a CC the server can accept
        # the CC but reject the actual recipient, which must not be reported as sent.
        to = message["To"]
        if to in refused:
            code, reason = refused[to]
            if isinstance(reason, bytes):
                reason = reason.decode(errors="replace")
            raise RecipientRefused(f"Recipient refused by mail server: {code} {reason}")


class RecipientRefused(Exception):
    """The mail server rejected the recipient's address (other recipients such as CC may have been accepted)."""


class GmailApiSender:
    """Sends through the Gmail API using the OAuth token created by `python -m app.gmail_auth`."""

    def __init__(self):
        self.from_email = None  # Gmail fills in the authenticated account
        self.label = "Gmail API (OAuth)"
        self._service = None

    def __enter__(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(str(config.GMAIL_TOKEN_FILE), config.GMAIL_SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            config.GMAIL_TOKEN_FILE.write_text(creds.to_json())
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self

    def __exit__(self, *exc):
        self._service = None

    def send(self, message: EmailMessage) -> None:
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        self._service.users().messages().send(userId="me", body={"raw": raw}).execute()


def get_sender():
    """Returns the configured sender, preferring Gmail OAuth if it has been set up."""
    if config.GMAIL_TOKEN_FILE.exists():
        return GmailApiSender()
    if config.SMTP_USER and config.SMTP_PASSWORD:
        return SmtpSender()
    return None
