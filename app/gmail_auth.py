"""
One-time Gmail OAuth setup (optional - SMTP with an App Password works without it).

1. Create an OAuth "Desktop app" client in Google Cloud Console with the Gmail API enabled.
2. Save the downloaded file as credentials.json in the project root.
3. Run:  python -m app.gmail_auth
"""
from google_auth_oauthlib.flow import InstalledAppFlow

from app import config


def main():
    if not config.GMAIL_CREDENTIALS_FILE.exists():
        raise SystemExit(f"Missing {config.GMAIL_CREDENTIALS_FILE}. Download it from Google Cloud Console first.")
    flow = InstalledAppFlow.from_client_secrets_file(str(config.GMAIL_CREDENTIALS_FILE), config.GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)
    config.GMAIL_TOKEN_FILE.write_text(creds.to_json())
    print(f"Saved {config.GMAIL_TOKEN_FILE}. The app will now send through the Gmail API.")


if __name__ == "__main__":
    main()
