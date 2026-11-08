"""DELETE /api/account removes the user's personal data and their Auth account."""

import json
import os
import urllib.request
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.account import SupabaseAuthAdmin, get_auth_admin
from app.auth import CurrentUser, get_current_user, get_token_verifier
from app.db import get_db
from app.main import app
from tests.db.conftest import DATABASE_URL


class FakeAdmin:
    def __init__(self, fail: bool = False) -> None:
        self.deleted: list[uuid.UUID] = []
        self.fail = fail

    def delete_user(self, user_id: uuid.UUID) -> None:
        if self.fail:
            raise httpx2.ConnectError("auth service unreachable")
        self.deleted.append(user_id)


def connect() -> psycopg.Connection:
    try:
        return psycopg.connect(DATABASE_URL, connect_timeout=3)
    except psycopg.OperationalError as exc:
        if os.environ.get("REQUIRE_DB") == "1":
            raise
        pytest.skip(f"database not reachable: {exc}")


def add_user_with_history(conn: psycopg.Connection, user_id: uuid.UUID) -> uuid.UUID:
    conn.execute(
        "insert into auth.users (id, email) values (%s, %s)",
        (user_id, f"acc-{user_id}@example.test"),
    )
    row = conn.execute(
        "insert into recommendation_attempts (user_id, symptom_text, outcome) "
        "values (%s, 'invented private symptom', 'recommended') returning id",
        (user_id,),
    ).fetchone()
    assert row is not None
    conn.execute("insert into recommendation_points values (%s, 'ACC1', 1)", (row[0],))
    conn.execute(
        "insert into point_ratings (attempt_id, point_id, user_id, rating) "
        "values (%s, 'ACC1', %s, 5)",
        (row[0], user_id),
    )
    return uuid.UUID(str(row[0]))


def personal_rows(conn: psycopg.Connection, user_id: uuid.UUID) -> dict[str, int]:
    def count(sql: str) -> int:
        row = conn.execute(sql, (user_id,)).fetchone()
        assert row is not None
        return int(row[0])

    return {
        "attempts": count("select count(*) from recommendation_attempts where user_id = %s"),
        "sets": count(
            "select count(*) from recommendation_points p join recommendation_attempts a "
            "on a.id = p.attempt_id where a.user_id = %s"
        ),
        "ratings": count("select count(*) from point_ratings where user_id = %s"),
    }


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    conn = connect()
    conn.execute(
        "insert into points (id, name, location_text, instructions) values ('ACC1','X','Y','{Z}')"
    )
    conn.commit()

    def test_db() -> Iterator[psycopg.Connection]:
        with psycopg.connect(DATABASE_URL) as request_conn:
            yield request_conn

    app.dependency_overrides[get_db] = test_db
    try:
        yield conn
    finally:
        app.dependency_overrides.clear()
        conn.rollback()
        conn.execute("delete from auth.users where email like 'acc-%%@example.test'")
        conn.execute("delete from points where id = 'ACC1'")
        conn.commit()
        conn.close()


def test_deletes_all_personal_data_and_auth_user(conn: psycopg.Connection) -> None:
    alice, bob = uuid.uuid4(), uuid.uuid4()
    add_user_with_history(conn, alice)
    add_user_with_history(conn, bob)
    conn.commit()
    admin = FakeAdmin()
    app.dependency_overrides[get_auth_admin] = lambda: admin
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(alice, None)

    response = TestClient(app).delete("/api/account")

    assert response.status_code == 204
    assert admin.deleted == [alice]
    assert personal_rows(conn, alice) == {"attempts": 0, "sets": 0, "ratings": 0}
    assert personal_rows(conn, bob) == {"attempts": 1, "sets": 1, "ratings": 1}  # untouched


def test_auth_failure_is_retryable_and_data_is_already_gone(conn: psycopg.Connection) -> None:
    alice = uuid.uuid4()
    add_user_with_history(conn, alice)
    conn.commit()
    app.dependency_overrides[get_auth_admin] = lambda: FakeAdmin(fail=True)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(alice, None)

    response = TestClient(app).delete("/api/account")

    assert response.status_code == 502
    assert response.json()["error"]["retryable"] is True
    assert "unreachable" not in response.text
    assert personal_rows(conn, alice) == {"attempts": 0, "sets": 0, "ratings": 0}


def test_requires_authentication() -> None:
    assert TestClient(app).delete("/api/account").status_code == 401


def test_real_supabase_account_is_deleted(conn: psycopg.Connection) -> None:
    """End to end with local Supabase Auth (skipped when keys are not set)."""
    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not (service_key and anon_key):
        if os.environ.get("REQUIRE_DB") == "1":
            pytest.fail("SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY must be set")
        pytest.skip("Supabase keys not set")

    def auth(path: str, key: str, body: dict[str, Any]) -> Any:
        request = urllib.request.Request(
            f"{supabase_url}/auth/v1/{path}",
            method="POST",
            data=json.dumps(body).encode(),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read())

    email, password = f"acc-{uuid.uuid4()}@example.test", "test-password-123"
    user = auth(
        "admin/users", service_key, {"email": email, "password": password, "email_confirm": True}
    )
    token = auth("token?grant_type=password", anon_key, {"email": email, "password": password})
    user_id = uuid.UUID(user["id"])
    conn.execute(
        "insert into recommendation_attempts (user_id, symptom_text) values (%s, 'invented')",
        (user_id,),
    )
    conn.commit()
    get_token_verifier.cache_clear()
    app.dependency_overrides[get_auth_admin] = lambda: SupabaseAuthAdmin(supabase_url, service_key)

    response = TestClient(app).delete(
        "/api/account", headers={"Authorization": f"Bearer {token['access_token']}"}
    )

    assert response.status_code == 204
    assert conn.execute("select count(*) from auth.users where id = %s", (user_id,)).fetchone() == (
        0,
    )
    assert personal_rows(conn, user_id)["attempts"] == 0
