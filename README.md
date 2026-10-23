# Auto Mailer

Upload a list of email addresses or mobile numbers (CSV, PDF, Word .docx or TXT), write one
message, and it is sent **separately** to every person — by **email** from your own account, or by
**WhatsApp** from your own number. Nobody sees anyone else's address or number.

## Setup (once)

1. Install Python 3.11+ and Node.js 20+ (Node is only needed to build the web interface).
2. Copy `.env.example` to `.env` and fill in your account (or just double-click `run.bat` — it does this for you).
   - **Gmail / Google Workspace:** turn on 2-Step Verification, then create an App Password at
     Google Account → Security → App passwords. Put your email in `SMTP_USER` and the 16-letter
     app password in `SMTP_PASSWORD`.
   - **Outlook / Zoho / other:** change `SMTP_HOST` / `SMTP_PORT` (examples are in `.env.example`).

## Run

Double-click **`run.bat`** — it installs packages, builds the web interface the first time,
starts the app and opens http://127.0.0.1:8000.

Or manually:
```
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
python -m uvicorn app.main:app --port 8000
```

## Project layout

- `app/` – FastAPI backend (API under `/api/...`, sending, file parsing, SQLite jobs)
- `frontend/` – Next.js + Tailwind web interface. It is built as static files (`frontend/out`)
  that FastAPI serves, so everything still runs as one program on port 8000.
- `static/` – the original plain-HTML interface, still available at http://127.0.0.1:8000/classic

**Working on the interface:** run the backend as above, then in another terminal
`cd frontend && npm run dev` and open http://localhost:3000 (it calls the API on port 8000).
After changes, run `npm run build` again so port 8000 serves the new version.

## Use

1. **Recipients** – upload one or more files. Every email address found is listed (duplicates and
   invalid ones are skipped). You can edit the list by hand.
   - CSV: uses the `email` column if there is one, otherwise any cell containing an address.
   - PDF / Word / TXT: every email address in the text is picked up.
   - Excel: save as CSV first.
2. **Compose** – subject, message, optional CC (added to every email) and attachments.
   Use *Send test* to send yourself one copy first.
3. **Review & send** – confirm, then watch progress. Failed addresses show the reason and can be
   retried. Jobs are saved in `automailer.db`; if the app is closed mid-send it continues when
   restarted.

## WhatsApp

Switch to the **WhatsApp** tab at the top of the page.

1. Click **Connect WhatsApp**. A Chrome window opens with WhatsApp Web — scan the QR code with
   your phone (WhatsApp → Linked devices → Link a device). You only need to do this once; the login
   is kept in the `whatsapp_profile` folder.
2. Upload files: mobile numbers are picked up from them. In a CSV, columns named phone / mobile /
   whatsapp / contact / number are used. 10-digit numbers get +91 (change `WA_DEFAULT_COUNTRY_CODE`).
   GST numbers, PIN codes, dates and invoice numbers are ignored.
3. Write the message, add attachments if needed, and send. A Chrome window opens and sends to each
   number **one at a time** with a random 15–40 second pause. Leave that window open and the
   computer awake. Numbers that are not on WhatsApp are marked as failed.

**Important — read before using:**
- This is not an official WhatsApp service. It drives WhatsApp Web automatically, which breaks
  WhatsApp's terms. **Your number can be banned**, especially if you message many people who
  haven't saved your number or who report you. Don't use your main business number; start small.
- Sending to many people at the same time isn't possible with one number, and doing it quickly
  is the fastest way to get banned — so it is one by one, with a daily cap (`WA_DAILY_LIMIT`, 150).
- If WhatsApp changes its website, sending may stop working until the selectors at the top of
  `app/services/whatsapp_service.py` are updated.
- For large or important campaigns, use the official WhatsApp Business Cloud API instead.

## Limits

Email: Gmail allows about 500 emails/day (personal) or 2,000/day (Workspace). The app waits
`SEND_DELAY_SECONDS` (default 2) between emails to avoid being flagged as spam.

## Optional: Gmail API instead of App Password

If your company blocks App Passwords: create an OAuth *Desktop app* client in Google Cloud Console
with the Gmail API enabled, save it as `credentials.json` here, and run `python -m app.gmail_auth`.
When `token.json` exists, the app sends through the Gmail API automatically.

## Tests

```
python -m pytest                 # unit + API tests
pip install aiosmtpd
python tests/e2e/e2e.py          # end-to-end: real UI in Chrome, local mail server, fake WhatsApp page
```

The end-to-end test never contacts real people. It checks uploads (CSV/PDF/Word), test send,
full campaigns with CC and attachments over TLS + login, rejected addresses, retry, stop/resume,
resuming after an app restart, WhatsApp text/attachments/invalid numbers, and error messages.
It cannot prove the real WhatsApp Web still matches the page structure the app expects —
do a small real test with your own numbers after WhatsApp updates.
