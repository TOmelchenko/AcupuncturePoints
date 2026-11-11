"""Retrieve relevant knowledge chunks and candidate curated points for a symptom.

Two signals find candidates:
* category match — points curated for the interpreted categories (relevance 1.0);
* similar knowledge — points linked to the chunks most similar to the search terms
  (relevance = cosine similarity).
A point found by both gets a small bonus. Candidates with equal relevance (every
category match scores the same) are ordered by how similar their own knowledge
is to the search terms, so the same points do not always win. Fewer than three candidates above the
threshold means the match is insufficient: the caller asks for clarification or
reports no match instead of padding the list with weak points.

The caller embeds the search terms first (`embed_query`), so no database
connection is held during that AI call.
"""

from dataclasses import dataclass, field

import psycopg

from app.ai import AI
from app.interpretation import Interpretation
from app.points import PointRecord, get_points

CHUNK_LIMIT = 8
CATEGORY_RELEVANCE = 1.0
BOTH_SIGNALS_BONUS = 0.1
MIN_RELEVANCE = 0.5
REQUIRED_CANDIDATES = 3


@dataclass(frozen=True)
class Chunk:
    id: int
    content: str
    point_id: str | None
    source_title: str
    page: int | None
    similarity: float


@dataclass(frozen=True)
class Candidate:
    point: PointRecord
    relevance: float
    category_ids: list[str] = field(default_factory=list)
    similarity: float = 0.0  # best similarity of the point's own chunks; breaks relevance ties


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[Chunk]
    candidates: list[Candidate]  # relevant candidates, most relevant first

    @property
    def sufficient(self) -> bool:
        return len(self.candidates) >= REQUIRED_CANDIDATES


def search_chunks(conn: psycopg.Connection, embedding: list[float], limit: int) -> list[Chunk]:
    rows = conn.execute(
        "select c.id, c.content, c.point_id, s.title, c.page, "
        "1 - (c.embedding <=> %(e)s::extensions.vector) as similarity "
        "from knowledge_chunks c join sources s on s.id = c.source_id "
        "order by c.embedding <=> %(e)s::extensions.vector limit %(limit)s",
        {"e": str(embedding), "limit": limit},
    ).fetchall()
    return [Chunk(*row) for row in rows]


def category_points(conn: psycopg.Connection, category_ids: list[str]) -> dict[str, list[str]]:
    """Point id -> matched category ids."""
    if not category_ids:
        return {}
    rows = conn.execute(
        "select point_id, array_agg(category_id order by category_id) from point_categories "
        "where category_id = any(%s) group by point_id",
        (category_ids,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def point_similarity(
    conn: psycopg.Connection, embedding: list[float], point_ids: list[str]
) -> dict[str, float]:
    """Point id -> similarity of its most similar chunk (absent if it has no chunks)."""
    if not point_ids:
        return {}
    rows = conn.execute(
        "select point_id, max(1 - (embedding <=> %(e)s::extensions.vector)) "
        "from knowledge_chunks where point_id = any(%(ids)s) group by point_id",
        {"e": str(embedding), "ids": point_ids},
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def embed_query(ai: AI, interpretation: Interpretation) -> list[float]:
    return ai.embed(" ".join(interpretation.search_terms))


def retrieve(
    conn: psycopg.Connection, embedding: list[float], interpretation: Interpretation
) -> RetrievalResult:
    chunks = search_chunks(conn, embedding, CHUNK_LIMIT)
    by_category = category_points(conn, interpretation.category_ids)

    best_similarity: dict[str, float] = {}
    for chunk in chunks:
        if chunk.point_id:
            best_similarity[chunk.point_id] = max(
                best_similarity.get(chunk.point_id, 0.0), chunk.similarity
            )

    relevance: dict[str, float] = {}
    for point_id in by_category.keys() | best_similarity.keys():
        score = max(
            CATEGORY_RELEVANCE if point_id in by_category else 0.0,
            best_similarity.get(point_id, 0.0),
        )
        if point_id in by_category and point_id in best_similarity:
            score += BOTH_SIGNALS_BONUS
        if score >= MIN_RELEVANCE:
            relevance[point_id] = round(score, 4)

    points = get_points(conn, list(relevance))
    similarity = point_similarity(conn, embedding, list(relevance))
    candidates = [
        Candidate(points[pid], relevance[pid], by_category.get(pid, []), similarity.get(pid, 0.0))
        for pid in sorted(
            relevance, key=lambda pid: (-relevance[pid], -similarity.get(pid, 0.0), pid)
        )
        if pid in points
    ]
    return RetrievalResult(chunks=chunks, candidates=candidates)
