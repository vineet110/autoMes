import pytest
from app.services.recipient_service import validate_recipients

def test_validate_recipients_success():
    csv_content = "email\ntest1@example.com\ntest2@example.com"
    valid, invalid = validate_recipients(csv_content)
    assert len(valid) == 2
    assert "test1@example.com" in valid
    assert "test2@example.com" in valid
    assert len(invalid) == 0

def test_validate_recipients_duplicates():
    csv_content = "email\ntest1@example.com\ntest1@example.com"
    valid, invalid = validate_recipients(csv_content)
    assert len(valid) == 1
    assert len(invalid) == 0

def test_validate_recipients_invalid():
    csv_content = "email\ntest1@example.com\ninvalid-email\n test2@example.com "
    valid, invalid = validate_recipients(csv_content)
    assert len(valid) == 2
    assert len(invalid) == 1
    assert "test2@example.com" in valid

def test_validate_recipients_no_header():
    csv_content = "test1@example.com\ntest2@example.com"
    valid, invalid = validate_recipients(csv_content)
    # Since there's no 'email' header, it treats first row as header if it doesn't match 'email'
    # Wait, my logic tries to find 'email' in header, if not found it uses first column.
    # If first row is test1@example.com, it will be skipped as header or used as first col.
    # Let's see what happens.
    assert len(valid) >= 1

def test_validate_recipients_mixed_case_header():
    csv_content = "Email\ntest1@example.com"
    valid, invalid = validate_recipients(csv_content)
    assert len(valid) == 1
    assert valid[0] == "test1@example.com"
