"""Settings read from environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    database_url: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        supabase_url=os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/"),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        ),
    )
