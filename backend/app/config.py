"""Settings read from environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str  # how the backend reaches Supabase
    supabase_public_url: str  # how browsers reach Supabase (e.g. for Storage images)
    database_url: str


@lru_cache
def get_settings() -> Settings:
    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")
    return Settings(
        supabase_url=supabase_url,
        supabase_public_url=os.environ.get("SUPABASE_PUBLIC_URL", supabase_url).rstrip("/"),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        ),
    )
