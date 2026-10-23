import io

import docx
import pytest

from app.services.recipient_service import extract_recipients, parse_email_list, validate_recipients


def make_pdf(text: str) -> bytes:
    """Builds a minimal one-page PDF containing the given text."""
    stream = f"BT /F1 12 Tf 50 750 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = io.BytesIO(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + obj + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref))
    return out.getvalue()


def make_docx() -> bytes:
    document = docx.Document()
    document.add_paragraph("Contact alice@example.com or Bob <bob@example.org>.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Carol"
    table.rows[0].cells[1].text = "carol@example.net"
    document.add_paragraph("Duplicate: ALICE@example.com")
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def test_extract_from_pdf():
    emails, problems = extract_recipients("list.pdf", make_pdf("Send to john@example.com and jane@example.com"))
    assert emails == ["john@example.com", "jane@example.com"]
    assert problems == []


def test_extract_from_docx_paragraphs_and_tables():
    emails, _ = extract_recipients("list.docx", make_docx())
    assert emails == ["alice@example.com", "bob@example.org", "carol@example.net"]


def test_extract_from_txt():
    emails, _ = extract_recipients("list.txt", b"a@example.com; b@example.com\nnot-an-email")
    assert emails == ["a@example.com", "b@example.com"]


def test_extract_from_csv_any_column():
    content = b"Name,Company,Mail\nAlice,Acme,alice@example.com\nBob,Beta,bob@example.com\n"
    emails, _ = extract_recipients("list.csv", content)
    assert emails == ["alice@example.com", "bob@example.com"]


def test_csv_without_header_keeps_first_row():
    valid, invalid = validate_recipients("test1@example.com\ntest2@example.com")
    assert valid == ["test1@example.com", "test2@example.com"]
    assert invalid == []


def test_empty_file_reports_problem():
    emails, problems = extract_recipients("empty.txt", b"nothing here")
    assert emails == []
    assert problems


def test_unsupported_extension():
    with pytest.raises(ValueError):
        extract_recipients("list.xlsx", b"")


def test_parse_email_list():
    valid, invalid = parse_email_list("a@example.com, b@example.com;bad\nA@example.com")
    assert valid == ["a@example.com", "b@example.com"]
    assert len(invalid) == 1


# ---------------------------------------------------------------- phone numbers

def test_phones_from_text_skip_non_phone_numbers():
    text = ("Call 98765 43210 or +91-98765-43211. GST 27AAACK1234F1Z5, PIN 400001, "
            "invoice 123456789012, date 2024-01-15, US +1 415 555 2671")
    emails, problems = extract_recipients("list.txt", text.encode(), channel="whatsapp")
    assert emails == ["+919876543210", "+919876543211", "+14155552671"]


def test_phones_from_pdf():
    phones, _ = extract_recipients("list.pdf", make_pdf("Mobile: 9876543210"), channel="whatsapp")
    assert phones == ["+919876543210"]


def test_phones_from_csv_phone_column():
    content = b"Name,Mobile No,Pincode\nA,98765 43210,400001\nB,09876543212,400002\nC,12345,400003\nD,9876543210,1\n"
    phones, problems = extract_recipients("list.csv", content, channel="whatsapp")
    assert phones == ["+919876543210", "+919876543212"]
    assert len(problems) == 1 and "12345" in problems[0]


def test_parse_phone_list():
    from app.services.recipient_service import parse_phone_list
    valid, invalid = parse_phone_list("9876543210\n+44 7911 123456, bad\n+91 98765 43210")
    assert valid == ["+919876543210", "+447911123456"]
    assert len(invalid) == 1
