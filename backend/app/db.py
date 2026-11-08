"""Database access: one privileged connection pool for the backend.

The backend connects as a privileged role (bypassing RLS) and is responsible
for scoping every query of private data to the authenticated user.
"""

from collections.abc import Iterator
from functools import lru_cache

import psycopg
from psycopg_pool import ConnectionPool

from app.config import get_settings


@lru_cache
def get_pool() -> ConnectionPool:
    return ConnectionPool(get_settings().database_url, min_size=1, max_size=5, open=True)


def get_db() -> Iterator[psycopg.Connection]:
    """FastAPI dependency: a pooled connection, rolled back if left uncommitted."""
    with get_pool().connection() as conn:
        yield conn
