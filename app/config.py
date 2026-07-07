import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev")
    DATABASE_PATH = BASE_DIR / os.environ.get("DATABASE_PATH", "data/finance_insight.db")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    QUOTE_STALE_AFTER_HOURS = float(os.environ.get("QUOTE_STALE_AFTER_HOURS", 24))
    NEWS_STALE_AFTER_HOURS = float(os.environ.get("NEWS_STALE_AFTER_HOURS", 24))
