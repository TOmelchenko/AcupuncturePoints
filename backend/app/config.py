"""Settings read from environment variables (see .env.example)."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    supabase_url: str  # how the backend reaches Supabase
    supabase_public_url: str  # how browsers reach Supabase (e.g. for Storage images)
    database_url: str
    supabase_service_role_key: str  # backend only: used to delete Auth users
    cors_allowed_origins: list[str]  # browser origins allowed to call the API (if not same-origin)


@lru_cache
def get_settings() -> Settings:
    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321").rstrip("/")
    return Settings(
        supabase_url=supabase_url,
        supabase_public_url=os.environ.get("SUPABASE_PUBLIC_URL", supabase_url).rstrip("/"),
        database_url=os.environ.get(
            "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
        ),
        supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY", ""),
        cors_allowed_origins=cors_origins(),
    )


def cors_origins() -> list[str]:
    """CORS_ALLOWED_ORIGINS (comma-separated) plus https://FRONTEND_HOST if set (e.g. on Render)."""
    origins = [o.strip().rstrip("/") for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",")]
    if host := os.environ.get("FRONTEND_HOST", "").strip():
        origins.append(f"https://{host}")
    return [o for o in origins if o]
