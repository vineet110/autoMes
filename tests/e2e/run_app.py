"""Starts the real app, pointing WhatsApp at the fake site and using a throwaway profile/DB."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent
APP_DIR = HERE.parents[1]
sys.path.insert(0, str(APP_DIR))
os.chdir(APP_DIR)

from app import config  # noqa: E402
from app.services import whatsapp_service  # noqa: E402

whatsapp_service.WHATSAPP_URL = os.environ["FAKE_WA_URL"]
config.WA_PROFILE_DIR = HERE / "wa_profile"

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=int(sys.argv[1]))
