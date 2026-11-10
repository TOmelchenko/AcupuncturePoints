"""Rank candidate points: symptom relevance first, past ratings only as a tie-breaker.

The rating adjustment is bounded to ±MAX_RATING_ADJUSTMENT, so a point that is
clearly less relevant (by more than twice that) can never overtake a more
relevant one. Ratings are personal: only the requesting user's own ratings count,
and only those from attempts in an overlapping symptom category. The adjustment
starts at MIN_RATINGS and reaches full weight at FULL_WEIGHT_RATINGS.

Points the user rated poorly (average <= LOW_RATING) are dropped from the
candidates, but only when at least RECOMMENDATION_COUNT other candidates remain,
so the user still gets a full set of recommendations.
"""

import uuid
from dataclasses import dataclass

import psycopg

from app.retrieval import Candidate

MAX_RATING_ADJUSTMENT = 0.05
MIN_RATINGS = 1
FULL_WEIGHT_RATINGS = 3
LOW_RATING = 2.0
RECOMMENDATION_COUNT = 3


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


def is_low_rated(signal: RatingSignal | None) -> bool:
    return signal is not None and signal.count >= MIN_RATINGS and signal.average <= LOW_RATING


def rank(candidates: list[Candidate], signals: dict[str, RatingSignal]) -> list[Candidate]:
    def score(candidate: Candidate) -> float:
        return candidate.relevance + rating_adjustment(signals.get(candidate.point.id))

    ranked = sorted(candidates, key=lambda c: (-score(c), -c.relevance, c.point.id))
    kept = [c for c in ranked if not is_low_rated(signals.get(c.point.id))]
    return kept if len(kept) >= RECOMMENDATION_COUNT else ranked


def load_rating_signals(
    conn: psycopg.Connection, user_id: uuid.UUID, point_ids: list[str], category_ids: list[str]
) -> dict[str, RatingSignal]:
    """Average the user's own past ratings per point, from attempts sharing a symptom category."""
    if not point_ids or not category_ids:
        return {}
    rows = conn.execute(
        "select r.point_id, avg(r.rating)::float, count(*) from point_ratings r "
        "join recommendation_attempts a on a.id = r.attempt_id "
        "where r.user_id = %s and r.point_id = any(%s) and a.category_ids && %s::text[] "
        "group by r.point_id",
        (user_id, point_ids, category_ids),
    ).fetchall()
    return {row[0]: RatingSignal(average=row[1], count=row[2]) for row in rows}
