import base64
import mimetypes
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import List, Optional


def build_message(
    to_email: str,
    subject: str,
    body: str,
    cc_emails: Optional[List[str]] = None,
    attachments: Optional[List[tuple[str, bytes]]] = None,  # List of (filename, content)
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> EmailMessage:
    """
    Builds one individual email. The To header only ever contains a single
    recipient, so recipients never see each other's addresses.
    """
    message = EmailMessage()
    if from_email:
        message["From"] = formataddr((from_name, from_email)) if from_name else from_email
        message["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    message["To"] = to_email
    message["Subject"] = subject

    if cc_emails:
        message["Cc"] = ", ".join(cc_emails)

    message.set_content(body)

    for filename, content in attachments or []:
        mime_type, _ = mimetypes.guess_type(filename)
        maintype, subtype = (mime_type or "application/octet-stream").split("/", 1)
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

    return message


def construct_mime_email(
    to_email: str,
    subject: str,
    body: str,
    cc_emails: Optional[List[str]] = None,
    attachments: Optional[List[tuple[str, bytes]]] = None,  # List of (filename, content)
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
) -> str:
    """
    Constructs a MIME email and returns it as a base64url encoded string
    suitable for the Gmail API.
    """
    message = build_message(to_email, subject, body, cc_emails, attachments, from_email, from_name)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
