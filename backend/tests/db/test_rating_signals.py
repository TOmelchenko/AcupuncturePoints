import psycopg

from app.ranking import load_rating_signals
from tests.db.conftest import create_user


def rate(db: psycopg.Connection, categories: list[str], point_id: str, rating: int) -> None:
    user = create_user(db)
    row = db.execute(
        "insert into recommendation_attempts (user_id, symptom_text, category_ids, outcome) "
        "values (%s, 'invented', %s, 'recommended') returning id",
        (user, categories),
    ).fetchone()
    assert row is not None
    db.execute("insert into recommendation_points values (%s, %s, 1)", (row[0], point_id))
    db.execute(
        "insert into point_ratings (attempt_id, point_id, user_id, rating) values (%s, %s, %s, %s)",
        (row[0], point_id, user, rating),
    )


def test_signals_only_count_ratings_from_overlapping_categories(db: psycopg.Connection) -> None:
    db.execute(
        "insert into points (id, name, location_text, instructions) "
        "values ('RS1', 'X', 'Y', '{Press.}')"
    )
    rate(db, ["rs-head"], "RS1", 5)
    rate(db, ["rs-head", "rs-sleep"], "RS1", 3)
    rate(db, ["rs-knee"], "RS1", 1)  # different symptom category: ignored

    signals = load_rating_signals(db, ["RS1"], ["rs-head"])

    assert signals["RS1"].count == 2
    assert signals["RS1"].average == 4.0
    assert load_rating_signals(db, ["RS1"], []) == {}
    assert load_rating_signals(db, ["RS1"], ["rs-other"]) == {}
