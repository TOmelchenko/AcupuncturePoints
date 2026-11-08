"""Account deletion: remove all of a user's personal data, then their Auth account.

Personal data (attempts with the original symptom text, recommendation sets and
ratings) is deleted in one transaction first. The Supabase Auth user is then
deleted with the service-role key, which never leaves the backend. No analytics
are retained, so nothing needs anonymising.
"""

import logging
import uuid
from functools import lru_cache
from typing import Protocol

import httpx2
import psycopg

from app.config import get_settings
from app.errors import ApiError

log = logging.getLogger(__name__)

DELETE_FAILED = ApiError(
    502, "internal_error", "We couldn't delete your account. Please try again.", retryable=True
)


class AuthAdmin(Protocol):
    def delete_user(self, user_id: uuid.UUID) -> None: ...


class SupabaseAuthAdmin:
    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self.supabase_url = supabase_url
        self.service_role_key = service_role_key

    def delete_user(self, user_id: uuid.UUID) -> None:
        response = httpx2.delete(
            f"{self.supabase_url}/auth/v1/admin/users/{user_id}",
            headers={
                "apikey": self.service_role_key,
                "Authorization": f"Bearer {self.service_role_key}",
            },
            timeout=10.0,
        )
        if response.status_code == 404:
            return  # already gone
        response.raise_for_status()


@lru_cache
def get_auth_admin() -> AuthAdmin:
    settings = get_settings()
    return SupabaseAuthAdmin(settings.supabase_url, settings.supabase_service_role_key)


def delete_account(conn: psycopg.Connection, admin: AuthAdmin, user_id: uuid.UUID) -> None:
    conn.execute("delete from point_ratings where user_id = %s", (user_id,))
    conn.execute(
        "delete from recommendation_attempts where user_id = %s", (user_id,)
    )  # cascades sets
    conn.commit()
    try:
        admin.delete_user(user_id)
    except httpx2.HTTPError as exc:
        log.error("deleting auth user %s failed: %s", user_id, type(exc).__name__)
        raise DELETE_FAILED from None
    log.info("deleted account %s", user_id)
