# Development Progress Log

## Project Status
- [x] Phase 1: Environment Inspection & Docs
- [x] Phase 2: Recipient Validation & Email Construction
- [x] Phase 3: Job Persistence & Sending
- [x] Phase 4: Sending backends (SMTP App Password; optional Gmail API OAuth)
- [x] Phase 5: Minimal Frontend
- [x] Phase 6: Testing & Verification (automated; live send needs real credentials)

## Implemented Features
- Recipient import from CSV, PDF, DOCX, TXT (multi-file, validation, de-duplication, editable list).
- Compose: subject, plain-text body, common CC, attachments; test send; confirm dialog.
- Individual sequential sending in a background thread with a configurable delay.
- WhatsApp sending (user's choice: unofficial WhatsApp Web automation via Playwright + installed
  Chrome; user was told about ban risk and the official Cloud API alternative). One at a time,
  random 15-40 s delay, daily cap, phone extraction from CSV/PDF/DOCX/TXT with +91 default.
- SQLite job persistence, per-recipient result log, stop, retry failed, auto-resume on restart.

## Files
- `app/main.py` – FastAPI routes
- `app/config.py` – settings from `.env`
- `app/services/recipient_service.py` – file parsing / validation
- `app/services/email_service.py` – MIME message construction
- `app/services/sender_service.py` – SMTP and Gmail API senders
- `app/services/job_service.py` – SQLite jobs + sending loop
- `app/services/whatsapp_service.py` – WhatsApp Web automation (selectors at top of file)
- `app/gmail_auth.py` – optional one-time Gmail OAuth
- `frontend/` – Next.js app: pages `/`, `/campaigns/`, `/campaigns/view/?id=`, `/connections/`
- `static/` – classic UI (index.html, app.js, style.css), served at /classic
- `run.bat` – Windows launcher

## Technology Choices
- **Backend:** Python 3.11+ / FastAPI
- **Database:** SQLite (stdlib `sqlite3`)
- **Frontend:** Next.js 16 + Tailwind 4 + lucide-react in `frontend/`, `output: 'export'`, served by
  FastAPI from `frontend/out` (with a mapper for `__next.*.txt` prefetch files). Dev: `npm run dev`
  on :3000 calls API on :8000 via NEXT_PUBLIC_API_URL + CORS. Old vanilla UI kept at `/classic`.
- **Sending:** SMTP with App Password by default (works with any provider and needs no Google
  Cloud project); Gmail API via OAuth used automatically when `token.json` exists.
- **Parsing:** pypdf, python-docx

## Testing (2026-10-24)
- `tests/e2e/e2e.py`: 26 end-to-end checks, all passing. Bugs it found and fixed:
  SMTP recipient refused but CC accepted was marked "sent"; blocking SMTP/PDF work froze the whole
  server (now run_in_threadpool); hidden WhatsApp message box mistaken for an open chat; inputs
  typed before React hydration were lost (form disabled until ready); raw SMTP errors (now readable).

## Next Task
- Fill in `.env` and do a live test send.
- WhatsApp: QR login detection verified live; actual message/attachment sending selectors still
  need a live test with a logged-in number.
