"""Rank candidate points: symptom relevance first, past ratings only as a tie-breaker.

The rating adjustment is bounded to ±MAX_RATING_ADJUSTMENT, so a point that is
clearly less relevant (by more than twice that) can never overtake a more
relevant one. Ratings count only when they come from attempts in an overlapping
symptom category and only once there are at least MIN_RATINGS of them; the
adjustment reaches full weight at FULL_WEIGHT_RATINGS.
"""

from dataclasses import dataclass

import psycopg

from app.retrieval import Candidate

MAX_RATING_ADJUSTMENT = 0.05
MIN_RATINGS = 3
FULL_WEIGHT_RATINGS = 10


@dataclass(frozen=True)
class RatingSignal:
    average: float  # 1-5 stars
    count: int


def rating_adjustment(signal: RatingSignal | None) -> float:
    if signal is None or signal.count < MIN_RATINGS:
        return 0.0
    centred = (signal.average - 3.0) / 2.0  # -1 (all 1-star) .. +1 (all 5-star)
    confidence = min(signal.count, FULL_WEIGHT_RATINGS) / FULL_WEIGHT_RATINGS
    return MAX_RATING_ADJUSTMENT * centred * confidence


def rank(candidates: list[Candidate], signals: dict[str, RatingSignal]) -> list[Candidate]:
    def score(candidate: Candidate) -> float:
        return candidate.relevance + rating_adjustment(signals.get(candidate.point.id))

    return sorted(candidates, key=lambda c: (-score(c), -c.relevance, c.point.id))


def load_rating_signals(
    conn: psycopg.Connection, point_ids: list[str], category_ids: list[str]
) -> dict[str, RatingSignal]:
    """Average past ratings per point, from attempts sharing a symptom category."""
    if not point_ids or not category_ids:
        return {}
    rows = conn.execute(
        "select r.point_id, avg(r.rating)::float, count(*) from point_ratings r "
        "join recommendation_attempts a on a.id = r.attempt_id "
        "where r.point_id = any(%s) and a.category_ids && %s::text[] group by r.point_id",
        (point_ids, category_ids),
    ).fetchall()
    return {row[0]: RatingSignal(average=row[1], count=row[2]) for row in rows}
