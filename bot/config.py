"""Settings loaded from environment variables (or a local, gitignored .env file)."""

import hashlib
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = _required("BOT_TOKEN")
DATABASE_URL = _required("DATABASE_URL")
ALLOWED_USER_ID = int(_required("ALLOWED_USER_ID"))

# Render sets RENDER_EXTERNAL_URL automatically; empty means local polling mode.
WEBHOOK_URL = (os.getenv("WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL") or "").rstrip("/")
PORT = int(os.getenv("PORT", "8443"))

# Telegram sends this in a header on every webhook call so fake requests are rejected.
# Derived from the token so there is nothing extra to configure.
WEBHOOK_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()

TZ = ZoneInfo("Asia/Jerusalem")
