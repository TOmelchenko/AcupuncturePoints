import psycopg
import pytest

from app.ai import FakeAI
from app.interpretation import Interpretation
from app.retrieval import RetrievalResult, embed_query
from app.retrieval import retrieve as retrieve_with_embedding

AI = FakeAI()


def interpretation(categories: list[str], terms: list[str]) -> Interpretation:
    return Interpretation(category_ids=categories, search_terms=terms, needs_clarification=False)


def retrieve(conn: psycopg.Connection, ai: FakeAI, interp: Interpretation) -> RetrievalResult:
    return retrieve_with_embedding(conn, embed_query(ai, interp), interp)


@pytest.fixture
def kb(db: psycopg.Connection) -> psycopg.Connection:
    """A small knowledge base with unique ids so it cannot clash with seed data."""
    db.execute(
        "insert into symptom_categories (id, name) values ('rt-cat-a', 'A'), ('rt-cat-b', 'B')"
    )
    for pid in ("RT1", "RT2", "RT3", "RT4", "RT5"):
        db.execute(
            "insert into points (id, name, location_text, instructions, duration) "
            "values (%s, %s, 'Somewhere.', '{Press.}', %s)",
            (pid, f"Point {pid}", "1 minute" if pid == "RT1" else None),
        )
    db.execute(
        "insert into point_categories values ('RT1','rt-cat-a'),('RT2','rt-cat-a'),"
        "('RT3','rt-cat-a'),('RT4','rt-cat-b')"
    )
    row = db.execute("insert into sources (title) values ('Retrieval test source') returning id")
    source_id = row.fetchone()[0]  # type: ignore[index]
    chunks = [
        ("RT4", 5, "zorblax quimby relief for zorblax quimby discomfort"),
        ("RT5", 6, "zorblax quimby pressing technique"),
        (None, 7, "an unrelated passage about walking"),
    ]
    for point_id, page, text in chunks:
        db.execute(
            "insert into knowledge_chunks (source_id, point_id, page, content, embedding) "
            "values (%s, %s, %s, %s, %s::extensions.vector)",
            (source_id, point_id, page, text, str(AI.embed(text))),
        )
    return db


def test_category_match_gives_candidates_with_full_records(kb: psycopg.Connection) -> None:
    result = retrieve(kb, AI, interpretation(["rt-cat-a"], ["nothing similar here"]))

    assert [c.point.id for c in result.candidates][:3] == ["RT1", "RT2", "RT3"]
    assert result.sufficient
    first = result.candidates[0]
    assert first.relevance == 1.0
    assert first.category_ids == ["rt-cat-a"]
    assert first.point.duration == "1 minute"
    assert first.point.instructions == ["Press."]


def test_similar_chunks_contribute_points_with_source_and_page(kb: psycopg.Connection) -> None:
    result = retrieve(kb, AI, interpretation([], ["zorblax quimby"]))

    top = result.chunks[0]
    assert top.source_title == "Retrieval test source"
    assert top.page in (5, 6)
    assert {c.point.id for c in result.candidates} >= {"RT4", "RT5"}
    assert all(0.5 <= c.relevance <= 1.1 for c in result.candidates)


def test_both_signals_rank_highest(kb: psycopg.Connection) -> None:
    result = retrieve(kb, AI, interpretation(["rt-cat-a", "rt-cat-b"], ["zorblax quimby relief"]))
    assert result.candidates[0].point.id == "RT4"
    assert result.candidates[0].relevance > 1.0


def test_weak_matches_are_insufficient_not_padded(kb: psycopg.Connection) -> None:
    result = retrieve(kb, AI, interpretation(["rt-cat-b"], ["completely different words"]))
    assert [c.point.id for c in result.candidates if c.point.id.startswith("RT")] == ["RT4"]
    assert not any(c.point.id == "RT5" for c in result.candidates)
    assert not result.sufficient


def test_no_categories_and_no_similar_text_finds_nothing_relevant(kb: psycopg.Connection) -> None:
    result = retrieve(kb, AI, interpretation([], ["qwertyuiop asdfgh"]))
    assert not any(c.point.id.startswith("RT") for c in result.candidates)


def test_equally_relevant_category_points_are_ordered_by_similarity(kb: psycopg.Connection) -> None:
    source_id = kb.execute("select id from sources where title = 'Retrieval test source'")
    kb.execute(
        "insert into knowledge_chunks (source_id, point_id, page, content, embedding) "
        "values (%s, 'RT3', 8, %s, %s::extensions.vector)",
        (source_id.fetchone()[0], "flumph wibble", str(AI.embed("flumph wibble"))),  # type: ignore[index]
    )
    # Push RT3's chunk out of the top chunks, so it only counts as a category match.
    for n in range(10):
        text = f"flumph wibble grobnar {n}"
        kb.execute(
            "insert into knowledge_chunks (source_id, point_id, page, content, embedding) "
            "select id, null, 9, %s, %s::extensions.vector from sources "
            "where title = 'Retrieval test source'",
            (text, str(AI.embed("flumph wibble grobnar"))),
        )

    result = retrieve(kb, AI, interpretation(["rt-cat-a"], ["flumph wibble grobnar"]))

    by_id = {c.point.id: c for c in result.candidates}
    assert by_id["RT1"].relevance == by_id["RT2"].relevance == by_id["RT3"].relevance == 1.0
    assert by_id["RT3"].similarity > 0.5 and by_id["RT1"].similarity == 0.0
    assert [c.point.id for c in result.candidates][:3] == ["RT3", "RT1", "RT2"]
