import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

_telegram_api_id = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_ID = int(_telegram_api_id) if _telegram_api_id else None
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_PHONE = os.getenv("TELEGRAM_PHONE")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "jobradar")

# Store the session file next to the backend project root regardless of the
# process's current working directory (e.g. `python -m app.telegram_login`
# vs `uvicorn app.main:app`).
BACKEND_DIR = Path(__file__).resolve().parent.parent
TELEGRAM_SESSION_PATH = str(BACKEND_DIR / TELEGRAM_SESSION_NAME)
