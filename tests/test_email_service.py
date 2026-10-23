from app.services.email_service import construct_mime_email
import base64

def test_construct_mime_email_basic():
    to = "recipient@example.com"
    subject = "Hello"
    body = "World"
    raw = construct_mime_email(to, subject, body)
    
    assert isinstance(raw, str)
    # Decode to check content
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert f"To: {to}" in decoded
    assert f"Subject: {subject}" in decoded
    assert body in decoded

def test_construct_mime_email_with_cc():
    to = "recipient@example.com"
    cc = ["cc1@example.com", "cc2@example.com"]
    raw = construct_mime_email(to, "Subj", "Body", cc_emails=cc)
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert "cc: cc1@example.com, cc2@example.com" in decoded.lower()

def test_construct_mime_email_with_attachments():
    to = "recipient@example.com"
    attachments = [("test.txt", b"hello world")]
    raw = construct_mime_email(to, "Subj", "Body", attachments=attachments)
    decoded = base64.urlsafe_b64decode(raw).decode("utf-8")
    assert "content-disposition: attachment; filename=\"test.txt\"" in decoded.lower()
