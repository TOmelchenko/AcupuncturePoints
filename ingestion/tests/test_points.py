from typing import Any

import psycopg

from ingestion.ai import FakeAI
from ingestion.points import categories_for, instructions_for, load_points, point_document


def point(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": "TP1",
        "name": "Test Point — Cè Shì",
        "summary": "A test point.",
        "location": "On the back of the test hand.",
        "description": ["A calming test point."],
        "helps_with": ["Headache acute", "Reflux", "Neck tension"],
        "tcm_effects": ["Calms the mind"],
        "contraindication": "None",
        "instructions": ["Press with the thumb.", "Repeat twice."],
        "duration": "30 seconds",
        "pressure": "Medium pressure",
    }
    return base | overrides


def test_categories_match_word_starts_only() -> None:
    assert categories_for(["Headache acute", "Reflux", "Neck tension"]) == [
        "headache",
        "digestion",
        "neck-shoulder",
    ]
    # "flu" must not match inside "reflux"; unmapped conditions get no category.
    assert "cold" not in categories_for(["Reflux"])
    assert categories_for(["Hypertension", "Diabetes"]) == []


def test_instructions_add_contraindication() -> None:
    assert instructions_for(point())[-1] == "Repeat twice."
    assert instructions_for(point(contraindication="Pregnancy"))[-1] == (
        "Do not use this point during pregnancy."
    )


def test_point_document_is_headed_by_code() -> None:
    doc = point_document(point())
    assert doc.startswith("TP1 Test Point — Cè Shì\n\nA test point.")
    assert "Helps with: Headache acute, Reflux, Neck tension" in doc
    assert "Location: On the back of the test hand." in doc


def test_load_points_upserts_points_categories_and_chunks(db: psycopg.Connection) -> None:
    data = {
        "source": {"title": "Test Web Atlas", "url": "https://example.org/", "language": "en"},
        "points": [point(), point(id="TP2", helps_with=["Insomnia"], contraindication="Pregnancy")],
    }

    assert load_points(db, FakeAI(), data) == (2, 2)
    # Re-running replaces chunks and category links instead of duplicating them.
    assert load_points(db, FakeAI(), data) == (2, 2)

    rows = db.execute(
        "select id, location_text, instructions, duration, pressure from points "
        "where id in ('TP1', 'TP2') order by id"
    ).fetchall()
    assert rows[0] == (
        "TP1",
        "On the back of the test hand.",
        ["Press with the thumb.", "Repeat twice."],
        "30 seconds",
        "Medium pressure",
    )
    assert rows[1][2][-1] == "Do not use this point during pregnancy."
    links = db.execute(
        "select point_id, category_id from point_categories "
        "where point_id in ('TP1', 'TP2') order by 1, 2"
    ).fetchall()
    assert links == [
        ("TP1", "digestion"),
        ("TP1", "headache"),
        ("TP1", "neck-shoulder"),
        ("TP2", "sleep"),
    ]
    chunks = db.execute(
        "select c.point_id, c.page from knowledge_chunks c join sources s on s.id = c.source_id "
        "where s.title = 'Test Web Atlas' order by 1"
    ).fetchall()
    assert chunks == [("TP1", None), ("TP2", None)]
