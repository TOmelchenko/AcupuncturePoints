"""GET /api/recommendations and /api/recommendations/{id} against the real database."""

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
    acting_as: uuid.UUID

    def add_attempt(self, outcome: str, minutes_ago: int, **fields: Any) -> uuid.UUID:
        row = self.conn.execute(
            "insert into recommendation_attempts "
            "(user_id, symptom_text, outcome, clarification_question, clarification_answer, "
            "created_at) values (%s, %s, %s, %s, %s, now() - make_interval(mins => %s)) "
            "returning id",
            (
                fields.get("user", self.alice),
                fields.get("symptom", f"invented {outcome}"),
                outcome,
                fields.get("question"),
                fields.get("answer"),
                minutes_ago,
            ),
        ).fetchone()
        assert row is not None
        for rank, pid in enumerate(fields.get("points", []), start=1):
            self.conn.execute(
                "insert into recommendation_points values (%s, %s, %s)", (row[0], pid, rank)
            )
        self.conn.commit()
        attempt_id: uuid.UUID = row[0]
        return attempt_id

    def rate(self, attempt_id: uuid.UUID, point_id: str, rating: int) -> None:
        self.conn.execute(
            "insert into point_ratings (attempt_id, point_id, user_id, rating) "
            "values (%s, %s, %s, %s)",
            (attempt_id, point_id, self.alice, rating),
        )
        self.conn.commit()

    def history(self, query: str = "") -> Any:
        response = self.client.get(f"/api/recommendations{query}")
        assert response.status_code == 200
        return response.json()


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
    for pid in ("HI1", "HI2", "HI3"):
        conn.execute(
            "insert into points (id, name, location_text, instructions, duration) "
            "values (%s, %s, 'Where', '{Press,Hold}', '1 minute')",
            (pid, f"Point {pid}"),
        )
    conn.commit()

    state = Env(TestClient(app), conn, alice, bob, acting_as=alice)
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
        conn.execute("delete from points where id like 'HI%%'")
        conn.commit()
        conn.close()


POINTS = ["HI1", "HI2", "HI3"]


def test_lists_own_attempts_newest_first_without_failed_or_pending(env: Env) -> None:
    recommended = env.add_attempt("recommended", 30, points=POINTS)
    asked = env.add_attempt("clarification_needed", 20, question="Where?")
    no_match = env.add_attempt("no_match", 10)
    env.add_attempt("failed", 5)
    env.add_attempt("pending", 1)
    env.rate(recommended, "HI2", 4)

    page = env.history()
    assert page["has_more"] is False
    assert [i["attempt_id"] for i in page["items"]] == [str(no_match), str(asked), str(recommended)]
    outcomes = [i["outcome"] for i in page["items"]]
    assert outcomes == ["no_match", "clarification_needed", "recommended"]
    assert page["items"][0]["points"] == []
    assert page["items"][2]["symptom"] == "invented recommended"
    assert page["items"][2]["points"] == [
        {"point_id": "HI1", "name": "Point HI1", "rating": None},
        {"point_id": "HI2", "name": "Point HI2", "rating": 4},
        {"point_id": "HI3", "name": "Point HI3", "rating": None},
    ]


def test_history_is_paged(env: Env) -> None:
    ids = [env.add_attempt("no_match", minutes) for minutes in (1, 2, 3)]
    first = env.history("?limit=2")
    assert [i["attempt_id"] for i in first["items"]] == [str(i) for i in ids[:2]]
    assert first["has_more"] is True
    second = env.history("?limit=2&offset=2")
    assert [i["attempt_id"] for i in second["items"]] == [str(ids[2])]
    assert second["has_more"] is False


def test_detail_shows_curated_points_with_ratings(env: Env) -> None:
    attempt = env.add_attempt(
        "recommended", 5, points=POINTS, question="Where?", answer="Left side"
    )
    env.rate(attempt, "HI3", 5)

    response = env.client.get(f"/api/recommendations/{attempt}")
    assert response.status_code == 200
    body = response.json()
    assert body["outcome"] == "recommended"
    assert (body["clarification_question"], body["clarification_answer"]) == ("Where?", "Left side")
    assert [(p["point_id"], p["rank"], p["rating"]) for p in body["points"]] == [
        ("HI1", 1, None),
        ("HI2", 2, None),
        ("HI3", 3, 5),
    ]
    assert body["points"][0]["instructions"] == ["Press", "Hold"]
    assert body["points"][0]["duration"] == "1 minute"


def test_detail_of_unanswered_clarification_has_no_points(env: Env) -> None:
    attempt = env.add_attempt("clarification_needed", 5, question="Where?")
    body = env.client.get(f"/api/recommendations/{attempt}").json()
    assert body["points"] == []
    assert body["clarification_question"] == "Where?"
    assert body["clarification_answer"] is None


def test_other_users_and_hidden_attempts_are_not_found(env: Env) -> None:
    bobs = env.add_attempt("recommended", 5, user=env.bob, points=POINTS)
    failed = env.add_attempt("failed", 5)
    assert env.history()["items"] == []
    for attempt in (bobs, failed, uuid.uuid4()):
        response = env.client.get(f"/api/recommendations/{attempt}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
