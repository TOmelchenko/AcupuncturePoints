import uuid

import psycopg
import pytest

from tests.db.conftest import create_user


def add_point(conn: psycopg.Connection, point_id: str = "TST1") -> str:
    conn.execute(
        "insert into points (id, name, location_text, instructions) values (%s, %s, %s, %s)",
        (point_id, "Test Point", "Between two test landmarks.", ["Press gently."]),
    )
    return point_id


def add_attempt(conn: psycopg.Connection, user_id: uuid.UUID) -> uuid.UUID:
    row = conn.execute(
        "insert into recommendation_attempts (user_id, symptom_text) values (%s, %s) returning id",
        (user_id, "invented test symptom"),
    ).fetchone()
    assert row is not None
    return uuid.UUID(str(row[0]))


def test_point_without_image_is_valid(db: psycopg.Connection) -> None:
    add_point(db)
    row = db.execute("select image_path, duration, pressure from points where id = 'TST1'")
    assert row.fetchone() == (None, None, None)


def test_point_image_requires_attribution_and_license(db: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into points (id, name, location_text, instructions, image_path) "
            "values ('TST2', 'X', 'Y', '{step}', 'points/tst2.png')"
        )


def test_point_requires_instructions(db: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into points (id, name, location_text, instructions) "
            "values ('TST3', 'X', 'Y', '{}')"
        )


def test_rating_must_be_between_1_and_5(db: psycopg.Connection) -> None:
    user_id = create_user(db)
    point_id = add_point(db)
    attempt_id = add_attempt(db, user_id)
    db.execute(
        "insert into recommendation_points (attempt_id, point_id, rank) values (%s, %s, 1)",
        (attempt_id, point_id),
    )
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into point_ratings (attempt_id, point_id, user_id, rating) "
            "values (%s, %s, %s, 6)",
            (attempt_id, point_id, user_id),
        )


def test_rating_requires_point_in_recommendation_set(db: psycopg.Connection) -> None:
    user_id = create_user(db)
    point_id = add_point(db)
    attempt_id = add_attempt(db, user_id)
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        db.execute(
            "insert into point_ratings (attempt_id, point_id, user_id, rating) "
            "values (%s, %s, %s, 4)",
            (attempt_id, point_id, user_id),
        )


def test_unknown_outcome_is_rejected(db: psycopg.Connection) -> None:
    user_id = create_user(db)
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "insert into recommendation_attempts (user_id, symptom_text, outcome) "
            "values (%s, 'x', 'guessed')",
            (user_id,),
        )


def test_deleting_user_removes_all_personal_data(db: psycopg.Connection) -> None:
    user_id = create_user(db)
    point_id = add_point(db)
    attempt_id = add_attempt(db, user_id)
    db.execute(
        "insert into recommendation_points (attempt_id, point_id, rank) values (%s, %s, 1)",
        (attempt_id, point_id),
    )
    db.execute(
        "insert into point_ratings (attempt_id, point_id, user_id, rating) values (%s, %s, %s, 5)",
        (attempt_id, point_id, user_id),
    )

    db.execute("delete from auth.users where id = %s", (user_id,))

    def count(sql: str) -> int:
        row = db.execute(sql, (attempt_id,)).fetchone()
        assert row is not None
        return int(row[0])

    assert count("select count(*) from recommendation_attempts where id = %s") == 0
    assert count("select count(*) from recommendation_points where attempt_id = %s") == 0
    assert count("select count(*) from point_ratings where attempt_id = %s") == 0
    # Curated content is not personal data and stays.
    assert db.execute("select count(*) from points where id = %s", (point_id,)).fetchone() == (1,)
