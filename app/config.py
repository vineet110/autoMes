import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")  # Google shows app passwords with spaces
FROM_NAME = os.getenv("FROM_NAME", "")

# Pause between messages so the provider does not flag the account as spam.
SEND_DELAY_SECONDS = float(os.getenv("SEND_DELAY_SECONDS", "2"))
MAX_ATTACHMENT_MB = float(os.getenv("MAX_ATTACHMENT_MB", "20"))

DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "automailer.db"))
GMAIL_CREDENTIALS_FILE = BASE_DIR / "credentials.json"
GMAIL_TOKEN_FILE = BASE_DIR / "token.json"
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# --- WhatsApp (sent through WhatsApp Web in a real browser window) ---
WA_DEFAULT_COUNTRY_CODE = os.getenv("WA_DEFAULT_COUNTRY_CODE", "91")
WA_BROWSER = os.getenv("WA_BROWSER", "chrome")  # chrome or msedge
# Random pause between messages; sending too fast is the main reason numbers get banned.
WA_MIN_DELAY_SECONDS = float(os.getenv("WA_MIN_DELAY_SECONDS", "15"))
WA_MAX_DELAY_SECONDS = float(os.getenv("WA_MAX_DELAY_SECONDS", "40"))
WA_DAILY_LIMIT = int(os.getenv("WA_DAILY_LIMIT", "150"))
WA_PROFILE_DIR = BASE_DIR / "whatsapp_profile"
