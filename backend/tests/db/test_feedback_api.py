"""POST /api/recommendations/{id}/points/{point_id}/feedback against the real database."""

import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.main import app
from tests.db.conftest import DATABASE_URL


@dataclass
class Env:
    client: TestClient
    conn: psycopg.Connection
    alice: uuid.UUID
    bob: uuid.UUID
    attempt_id: uuid.UUID  # Alice's attempt recommending FB1, FB2, FB3
    acting_as: uuid.UUID

    def rate(self, point_id: str, rating: Any, attempt_id: uuid.UUID | None = None) -> Any:
        attempt = attempt_id or self.attempt_id
        return self.client.post(
            f"/api/recommendations/{attempt}/points/{point_id}/feedback", json={"rating": rating}
        )

    def stored(self) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            "select point_id, rating from point_ratings where attempt_id = %s order by point_id",
            (self.attempt_id,),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]


@pytest.fixture
def env() -> Iterator[Env]:
    try:
        conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
    except psycopg.OperationalError as exc:
        if os.environ.get("REQUIRE_DB") == "1":
            raise
        pytest.skip(f"database not reachable: {exc}")
    alice, bob = uuid.uuid4(), uuid.uuid4()
    for user in (alice, bob):
        conn.execute(
            "insert into auth.users (id, email) values (%s, %s)", (user, f"{user}@example.test")
        )
    for pid in ("FB1", "FB2", "FB3", "FB4"):
        conn.execute(
            "insert into points (id, name, location_text, instructions) "
            "values (%s, 'X', 'Y', '{Z}')",
            (pid,),
        )
    row = conn.execute(
        "insert into recommendation_attempts (user_id, symptom_text, outcome) "
        "values (%s, 'invented', 'recommended') returning id",
        (alice,),
    ).fetchone()
    assert row is not None
    for rank, pid in enumerate(("FB1", "FB2", "FB3"), start=1):
        conn.execute("insert into recommendation_points values (%s, %s, %s)", (row[0], pid, rank))
    conn.commit()

    state = Env(TestClient(app), conn, alice, bob, row[0], acting_as=alice)
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(state.acting_as, None)

    def test_db() -> Iterator[psycopg.Connection]:
        with psycopg.connect(DATABASE_URL) as request_conn:
            yield request_conn

    app.dependency_overrides[get_db] = test_db
    try:
        yield state
    finally:
        app.dependency_overrides.clear()
        conn.rollback()
        conn.execute("delete from auth.users where id = any(%s)", ([alice, bob],))
        conn.execute("delete from points where id like 'FB%%'")
        conn.commit()
        conn.close()


def test_each_point_is_rated_independently(env: Env) -> None:
    for point_id, rating in [("FB1", 5), ("FB2", 2), ("FB3", 4)]:
        response = env.rate(point_id, rating)
        assert response.status_code == 200
        assert response.json() == {
            "attempt_id": str(env.attempt_id),
            "point_id": point_id,
            "rating": rating,
        }
    assert env.stored() == [("FB1", 5), ("FB2", 2), ("FB3", 4)]


def test_rating_again_replaces_the_earlier_rating(env: Env) -> None:
    env.rate("FB1", 2)
    env.rate("FB1", 4)
    assert env.stored() == [("FB1", 4)]


@pytest.mark.parametrize("rating", [0, 6, "five", None])
def test_ratings_outside_1_to_5_are_rejected(env: Env, rating: Any) -> None:
    response = env.rate("FB1", rating)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert env.stored() == []


def test_point_not_in_the_recommendation_set_is_rejected(env: Env) -> None:
    response = env.rate("FB4", 5)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_another_users_attempt_cannot_be_rated(env: Env) -> None:
    env.acting_as = env.bob
    assert env.rate("FB1", 5).status_code == 404
    assert env.rate("FB1", 5, attempt_id=uuid.uuid4()).status_code == 404
    assert env.stored() == []
