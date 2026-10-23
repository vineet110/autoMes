"""
Sends WhatsApp messages by driving WhatsApp Web in a real browser window (Playwright).

This is NOT an official WhatsApp API. It uses the user's own number, breaks WhatsApp's
terms of service, and can get the number banned if used too aggressively. It can also
stop working whenever WhatsApp changes its website; the selectors below are the part
that would need updating.

The login session is kept in WA_PROFILE_DIR, so the QR code only has to be scanned once.
Only one browser can use that profile at a time, hence the module-level lock.
"""
import mimetypes
import threading
import time
from typing import List, Optional
from urllib.parse import quote

from app import config

WHATSAPP_URL = "https://web.whatsapp.com"
LOGGED_IN = "#pane-side"
QR_CODE = "canvas[aria-label*='Scan'], div[data-ref] canvas"
# Only visible boxes count: a hidden one may linger while the page decides the number is invalid.
MESSAGE_BOX = "footer div[contenteditable='true'] >> visible=true"
INVALID_NUMBER_TEXT = "shared via url is invalid"  # "Phone number shared via url is invalid."
ATTACH_BUTTON = ("button[title='Attach'], div[title='Attach'], [aria-label='Attach'], "
                 "span[data-icon='plus-rounded'], span[data-icon='plus'], span[data-icon='clip']")
MEDIA_SEND_BUTTON = "div[role='dialog'] span[data-icon='send'], span[data-icon='wds-ic-send-filled'], div[aria-label='Send']"
PENDING_ICON = "#main span[data-icon='msg-time']"

browser_lock = threading.Lock()
_login_state = {"status": "unknown", "detail": ""}


class WhatsAppError(Exception):
    pass


def _marker():
    # Written when WhatsApp Web shows the chat list, so we know a login succeeded at least once.
    return config.WA_PROFILE_DIR / "automailer_logged_in"


def login_state() -> dict:
    if _login_state["status"] == "unknown" and _marker().exists():
        return {"status": "probably_logged_in", "detail": "Logged in previously."}
    return dict(_login_state)


def _launch(playwright):
    context = playwright.chromium.launch_persistent_context(
        str(config.WA_PROFILE_DIR),
        channel=config.WA_BROWSER,
        headless=False,  # WhatsApp Web refuses headless browsers, and the user should see what is sent
        viewport={"width": 1100, "height": 800},
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.on("dialog", lambda dialog: dialog.accept())  # "Leave site?" prompts between chats
    return context, page


def _wait_for_login(page, timeout_s: float) -> None:
    page.goto(WHATSAPP_URL)
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.locator(LOGGED_IN).count():
            _login_state.update(status="logged_in", detail="")
            _marker().touch()
            return
        if page.locator(QR_CODE).count():
            _login_state.update(status="waiting_for_qr", detail="Scan the QR code in the browser window with your phone.")
        page.wait_for_timeout(1000)
    _marker().unlink(missing_ok=True)
    _login_state.update(status="logged_out", detail="Not logged in. Click 'Connect WhatsApp' and scan the QR code.")
    raise WhatsAppError(_login_state["detail"])


def login(timeout_s: float = 180) -> None:
    """Opens WhatsApp Web so the user can scan the QR code. Runs in a background thread."""
    from playwright.sync_api import sync_playwright

    if not browser_lock.acquire(blocking=False):
        _login_state.update(status="busy", detail="WhatsApp is busy sending. Try again when it finishes.")
        return
    try:
        _login_state.update(status="starting", detail="Opening browser…")
        with sync_playwright() as p:
            context, page = _launch(p)
            try:
                _wait_for_login(page, timeout_s)
                page.wait_for_timeout(3000)  # let WhatsApp finish syncing before closing
            finally:
                context.close()
    except WhatsAppError:
        pass
    except Exception as e:
        _login_state.update(status="error", detail=str(e)[:300])
    finally:
        browser_lock.release()


class WhatsAppSender:
    """Context manager: opens the browser once per job, then sends one chat at a time."""

    def __init__(self):
        self._playwright = None
        self._context = None
        self._page = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        try:
            self._context, self._page = _launch(self._playwright)
            _wait_for_login(self._page, timeout_s=120)
        except Exception:
            self.__exit__()
            raise
        return self

    def __exit__(self, *exc):
        try:
            if self._context:
                self._context.close()
        finally:
            if self._playwright:
                self._playwright.stop()
            self._context = self._page = self._playwright = None

    def send(self, phone: str, text: str, attachments: Optional[List[tuple[str, bytes]]] = None) -> None:
        page = self._page
        number = phone.lstrip("+")
        page.goto(f"{WHATSAPP_URL}/send?phone={number}&text={quote(text)}")

        # Wait for either the chat to open or the "invalid number" popup.
        deadline = time.time() + 60
        while True:
            if page.locator(MESSAGE_BOX).count():
                break
            if page.get_by_text(INVALID_NUMBER_TEXT, exact=False).count():
                raise WhatsAppError("This number is not on WhatsApp.")
            if time.time() > deadline:
                raise WhatsAppError("Chat did not open within 60 seconds.")
            page.wait_for_timeout(500)

        box = page.locator(MESSAGE_BOX).last
        if text.strip():
            # The text is pre-filled from the URL; wait until it shows up, then send.
            for _ in range(20):
                if box.inner_text().strip():
                    break
                page.wait_for_timeout(500)
            else:
                raise WhatsAppError("Message text did not load into the chat box.")
            box.click()
            page.keyboard.press("Enter")

        for filename, content in attachments or []:
            self._send_attachment(filename, content)

        self._wait_until_delivered_to_server()

    def _send_attachment(self, filename: str, content: bytes) -> None:
        page = self._page
        page.locator(ATTACH_BUTTON).first.click()
        file_input = page.locator("input[type='file']").first
        file_input.wait_for(state="attached", timeout=10000)
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        file_input.set_input_files({"name": filename, "mimeType": mime_type, "buffer": content})
        try:
            page.locator(MEDIA_SEND_BUTTON).first.click(timeout=30000)
        except Exception as e:
            raise WhatsAppError(f"Could not send attachment {filename}: {e}") from e
        page.wait_for_timeout(1500)

    def _wait_until_delivered_to_server(self) -> None:
        # A clock icon means "still sending"; leaving the chat before it clears can lose the message.
        page = self._page
        page.wait_for_timeout(1500)
        deadline = time.time() + 60
        while page.locator(PENDING_ICON).count():
            if time.time() > deadline:
                raise WhatsAppError("Message is stuck as pending (check your phone's internet connection).")
            page.wait_for_timeout(1000)
