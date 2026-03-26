"""
Loyiha konfiguratsiyasi
"""

import os
import random
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Brauzer
    HEADLESS: bool = True
    BROWSER_TIMEOUT: int = 30
    ELEMENT_TIMEOUT: int = 15
    PAGE_LOAD_WAIT: float = 3.0

    # ── Scraping
    MAX_VIDEOS: int = 10
    MAX_COMMENTS: int = 10
    SCROLL_PAUSE: float = 2.0
    MAX_SCROLL_ATTEMPTS: int = 5
    MIN_DELAY: float = 2.0
    MAX_DELAY: float = 5.0

    # ── Output
    OUTPUT_DIR: str = "output"

    # ── Video
    SHORTS_MAX_DURATION_SEC: int = 60

    # ── Retry
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 5.0

    # ── PostgreSQL Yoki .env dan oladi, yoki default qiymatni oladi
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db"
    )

    # Sync URL — Alembic migration uchun
    DATABASE_URL_SYNC: str = os.getenv(
        "DATABASE_URL_SYNC", "postgresql+asyncpg://user:pass@localhost:5432/db"
    )

    @classmethod
    def get_random_delay(cls) -> float:
        return random.uniform(cls.MIN_DELAY, cls.MAX_DELAY)
