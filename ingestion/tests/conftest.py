import os
from collections.abc import Iterator

import psycopg
import pytest

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)


@pytest.fixture
def db() -> Iterator[psycopg.Connection]:
    """A local Supabase connection rolled back after each test (skipped if unreachable)."""
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
    except psycopg.OperationalError as exc:
        if os.environ.get("REQUIRE_DB") == "1":
            raise
        pytest.skip(f"database not reachable: {exc}")
    try:
        yield conn
    finally:
        conn.rollback()
        conn.close()
