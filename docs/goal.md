# Project Goal: Minimal Bulk Email Automation Sender

## Exact Project Goal
Build a simple web application that lets an authorized user send the same professional email individually to multiple recipients through their own company Gmail account.

## Required Email-Sending Behavior
- Send separate messages to each recipient.
- **To:** The current recipient's email address only.
- **CC:** Common CC list configured by the user (optional).
- **Subject:** Same configured subject.
- **Body:** Same configured email body (plain text).
- **Attachments:** Same selected attachments.
- **Sender:** Authenticated user's Gmail account.

## Privacy Requirement
Recipients must never see other recipients' email addresses. Never place the entire recipient list in To or CC. Do not use BCC as a substitute for individual delivery.

## Minimum Required Features
1. Gmail OAuth 2.0 Authentication.
2. CSV Recipient Import (with validation and de-duplication).
3. Email Composition (Subject, Body, CC, Attachments).
4. Preview and Confirmation before sending.
5. Sequential individual sending via Gmail API.
6. Progress tracking and individual result logging.
7. Reliability: Job persistence in SQLite, retry for failed messages.
8. Responsive UI (Next.js + Tailwind; original plain HTML UI kept at /classic).

## Explicit Non-Goals
- ~~No UI frameworks~~ — changed 2026-10-23 at the user's request: frontend is Next.js (static export) served by FastAPI.
- No complex marketing features (dashboards, analytics, templates).
- No parallel sending (initially).
- No paid APIs or third-party email platforms.
- No containerization (Docker/Kubernetes) unless necessary.

## Reminder
Do not deviate from the original goal. Do not add unnecessary features, frameworks, services, abstractions, or UI components. Implement the smallest reliable solution that satisfies the requirements.
