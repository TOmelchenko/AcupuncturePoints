"""The development seed covers every display variant the UI must handle."""

from pathlib import Path

import psycopg
import pytest

SEED_SQL = Path(__file__).parents[3] / "db" / "seed" / "seed.sql"
SEED_IMAGES = Path(__file__).parents[3] / "db" / "seed" / "images"


@pytest.fixture
def seeded(db: psycopg.Connection) -> psycopg.Connection:
    db.execute(SEED_SQL.read_text())  # rolled back after the test
    return db


def count(conn: psycopg.Connection, where: str) -> int:
    row = conn.execute(f"select count(*) from points where {where}").fetchone()
    assert row is not None
    return int(row[0])


@pytest.mark.parametrize("column", ["image_path", "duration", "pressure"])
def test_seed_has_points_with_and_without(seeded: psycopg.Connection, column: str) -> None:
    assert count(seeded, f"{column} is not null") >= 1
    assert count(seeded, f"{column} is null") >= 1


def test_every_seed_image_file_exists(seeded: psycopg.Connection) -> None:
    rows = seeded.execute("select image_path from points where image_path is not null").fetchall()
    for (image_path,) in rows:
        assert (SEED_IMAGES / Path(image_path).name).is_file(), image_path


def test_every_category_has_points(seeded: psycopg.Connection) -> None:
    rows = seeded.execute(
        "select c.id from symptom_categories c "
        "left join point_categories pc on pc.category_id = c.id "
        "group by c.id having count(pc.point_id) < 2"
    ).fetchall()
    assert rows == []
