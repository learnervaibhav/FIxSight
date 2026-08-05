"""Application configuration and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# Load .env placed in app/core only.
ENV_PATH = Path(__file__).resolve().with_name(".env")
load_dotenv(dotenv_path=ENV_PATH, override=False)


@dataclass(frozen=True)
class Settings:
    database_url: str
    google_api_key: str | None = None
    openai_api_key: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("DATABASE_URL is not set. Add it to your .env file.")

    google_api_key = os.getenv("GOOGLE_API_KEY")
    return Settings(database_url=database_url, google_api_key=google_api_key)