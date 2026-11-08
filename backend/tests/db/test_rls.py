"""Row Level Security: users see only their own private records."""

import json
import uuid
from dataclasses import dataclass

import psycopg
import pytest

from tests.db.conftest import create_user


@dataclass
class Fixture:
    alice: uuid.UUID
    bob: uuid.UUID
    alice_attempt: uuid.UUID
    bob_attempt: uuid.UUID


def act_as(conn: psycopg.Connection, user_id: uuid.UUID | None) -> None:
    """Switch the transaction to the Supabase role used for API requests."""
    if user_id is None:
        conn.execute("set local role anon")
        return
    claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
    conn.execute("select set_config('request.jwt.claims', %s, true)", (claims,))
    conn.execute("set local role authenticated")


@pytest.fixture
def data(db: psycopg.Connection) -> Fixture:
    db.execute(
        "insert into points (id, name, location_text, instructions) "
        "values ('RLS1', 'Test Point', 'Somewhere testable.', '{Press gently.}')"
    )
    alice, bob = create_user(db), create_user(db)
    attempts = {}
    for user in (alice, bob):
        row = db.execute(
            "insert into recommendation_attempts (user_id, symptom_text) "
            "values (%s, 'invented test symptom') returning id",
            (user,),
        ).fetchone()
        assert row is not None
        attempts[user] = row[0]
        db.execute(
            "insert into recommendation_points (attempt_id, point_id, rank) values (%s, 'RLS1', 1)",
            (row[0],),
        )
        db.execute(
            "insert into point_ratings (attempt_id, point_id, user_id, rating) "
            "values (%s, 'RLS1', %s, 4)",
            (row[0], user),
        )
    return Fixture(alice, bob, attempts[alice], attempts[bob])


def ids(conn: psycopg.Connection, sql: str) -> set[str]:
    return {str(row[0]) for row in conn.execute(sql).fetchall()}


def test_user_reads_only_own_attempts(db: psycopg.Connection, data: Fixture) -> None:
    act_as(db, data.alice)
    assert ids(db, "select id from recommendation_attempts") == {str(data.alice_attempt)}


def test_user_reads_only_own_recommendation_points(db: psycopg.Connection, data: Fixture) -> None:
    act_as(db, data.alice)
    assert ids(db, "select attempt_id from recommendation_points") == {str(data.alice_attempt)}


def test_user_reads_only_own_ratings(db: psycopg.Connection, data: Fixture) -> None:
    act_as(db, data.alice)
    assert ids(db, "select attempt_id from point_ratings") == {str(data.alice_attempt)}


def test_user_cannot_update_or_delete_other_users_records(
    db: psycopg.Connection, data: Fixture
) -> None:
    act_as(db, data.alice)
    updated = db.execute(
        "update recommendation_attempts set symptom_text = 'changed' where id = %s",
        (data.bob_attempt,),
    )
    assert updated.rowcount == 0
    deleted = db.execute("delete from point_ratings where attempt_id = %s", (data.bob_attempt,))
    assert deleted.rowcount == 0

    db.execute("reset role")
    row = db.execute(
        "select symptom_text from recommendation_attempts where id = %s", (data.bob_attempt,)
    ).fetchone()
    assert row == ("invented test symptom",)


def test_user_cannot_write_records_directly(db: psycopg.Connection, data: Fixture) -> None:
    """Writes go through the backend; even inserting for yourself is refused."""
    act_as(db, data.alice)
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        db.execute(
            "insert into recommendation_attempts (user_id, symptom_text) values (%s, 'x')",
            (data.alice,),
        )


def test_signed_in_user_can_read_but_not_change_curated_points(
    db: psycopg.Connection, data: Fixture
) -> None:
    act_as(db, data.alice)
    assert "RLS1" in ids(db, "select id from points")
    assert db.execute("update points set name = 'changed' where id = 'RLS1'").rowcount == 0


def test_anonymous_user_sees_nothing(db: psycopg.Connection, data: Fixture) -> None:
    act_as(db, None)
    assert ids(db, "select id from points") == set()
    assert ids(db, "select id from recommendation_attempts") == set()
