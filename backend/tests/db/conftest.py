"""Fixtures for tests that need the local Supabase database.

These tests are skipped when the database is not reachable, unless
REQUIRE_DB=1 is set (as in CI), in which case they fail instead.
"""

import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
)


@pytest.fixture
def db() -> Iterator[psycopg.Connection]:
    """A connection whose changes are rolled back after each test."""
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


def create_user(conn: psycopg.Connection) -> uuid.UUID:
    user_id = uuid.uuid4()
    conn.execute(
        "insert into auth.users (id, email) values (%s, %s)",
        (user_id, f"{user_id}@example.test"),
    )
    return user_id
