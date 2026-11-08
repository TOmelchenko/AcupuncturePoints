import json
from pathlib import Path

import psycopg

from ingestion.ai import FakeAI
from ingestion.load import load_all, mentioned_point


def write_pages(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
    return path


def source(title: str, language: str = "en") -> dict[str, object]:
    return {
        "file": "x.pdf",
        "title": title,
        "language": language,
        "author": "A. Author",
        "url": "https://example.org/x.pdf",
        "license": "CC BY 4.0",
    }


def test_mentioned_point_requires_exactly_one_code() -> None:
    ids = {"LI4", "PC6", "EX-HN3"}
    assert mentioned_point("Press LI4 gently.", ids) == "LI4"
    assert mentioned_point("Combine LI4 and PC6.", ids) is None
    assert mentioned_point("Use EX-HN3 between the brows.", ids) == "EX-HN3"
    assert mentioned_point("Not LI40 or XLI4.", ids) is None


def test_load_stores_chunks_with_metadata(db: psycopg.Connection, tmp_path: Path) -> None:
    db.execute(
        "insert into points (id, name, location_text, instructions) "
        "values ('TL1', 'Test', 'Here.', '{Press.}')"
    )
    pages = write_pages(
        tmp_path / "pages.jsonl",
        [
            {"source": source("Test Guide EN"), "page": 3, "text": "Press TL1 for tension relief."},
            {"source": source("Test Guide DE", "de"), "page": 7, "text": "Ein deutscher Text."},
        ],
    )

    total = load_all(db, FakeAI(), pages)

    assert total == 2
    rows = db.execute(
        "select s.title, s.language, s.license, c.page, c.language, c.point_id, c.content, "
        "vector_dims(c.embedding) from knowledge_chunks c join sources s on s.id = c.source_id "
        "where s.title like 'Test Guide%%' order by s.title desc"
    ).fetchall()
    assert rows[0] == (
        "Test Guide EN",
        "en",
        "CC BY 4.0",
        3,
        "en",
        "TL1",
        "Press TL1 for tension relief.",
        1024,
    )
    # Non-English source: original language kept on the source, content translated.
    assert rows[1][:6] == ("Test Guide DE", "de", "CC BY 4.0", 7, "en", None)
    assert rows[1][6] == "[translated from de] Ein deutscher Text."


def test_reloading_a_source_replaces_its_chunks(db: psycopg.Connection, tmp_path: Path) -> None:
    first = write_pages(
        tmp_path / "a.jsonl",
        [
            {"source": source("Test Reload"), "page": 1, "text": "Old text."},
            {"source": source("Test Reload"), "page": 2, "text": "More old text."},
        ],
    )
    second = write_pages(
        tmp_path / "b.jsonl",
        [
            {"source": source("Test Reload"), "page": 1, "text": "New text."},
        ],
    )

    load_all(db, FakeAI(), first)
    load_all(db, FakeAI(), second)

    rows = db.execute(
        "select c.content from knowledge_chunks c join sources s on s.id = c.source_id "
        "where s.title = 'Test Reload'"
    ).fetchall()
    assert rows == [("New text.",)]
    count = db.execute("select count(*) from sources where title = 'Test Reload'").fetchone()
    assert count == (1,)
