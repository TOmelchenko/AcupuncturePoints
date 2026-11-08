"""Per-point ratings for a user's own recommendation set."""

import uuid

import psycopg

from app.errors import ApiError
from app.schemas import FeedbackResponse

NOT_FOUND = ApiError(404, "not_found", "We couldn't find that recommendation to rate.")


def save_rating(
    conn: psycopg.Connection, user_id: uuid.UUID, attempt_id: uuid.UUID, point_id: str, rating: int
) -> FeedbackResponse:
    """Store or replace the rating; the point must belong to the user's own attempt."""
    owned = conn.execute(
        "select 1 from recommendation_points p "
        "join recommendation_attempts a on a.id = p.attempt_id "
        "where p.attempt_id = %s and p.point_id = %s and a.user_id = %s",
        (attempt_id, point_id, user_id),
    ).fetchone()
    if owned is None:
        raise NOT_FOUND
    conn.execute(
        "insert into point_ratings (attempt_id, point_id, user_id, rating) "
        "values (%s, %s, %s, %s) on conflict (attempt_id, point_id) "
        "do update set rating = excluded.rating, updated_at = now()",
        (attempt_id, point_id, user_id, rating),
    )
    conn.commit()
    return FeedbackResponse(attempt_id=attempt_id, point_id=point_id, rating=rating)
