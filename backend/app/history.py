"""A user's own past recommendation attempts, for the history page.

Failed and in-progress attempts are left out. Point details come from the
curated records, exactly as on the original recommendation.
"""

import uuid

import psycopg

from app.config import get_settings
from app.errors import ApiError
from app.points import get_points
from app.schemas import HistoryDetail, HistoryItem, HistoryPage, RatedPoint
from app.validation import build_points

VISIBLE_OUTCOMES = ["recommended", "clarification_needed", "no_match"]
NOT_FOUND = ApiError(404, "not_found", "We couldn't find that recommendation.")


def list_history(
    conn: psycopg.Connection, user_id: uuid.UUID, limit: int, offset: int
) -> HistoryPage:
    rows = conn.execute(
        "select a.id, a.created_at, a.symptom_text, a.outcome, "
        "coalesce(json_agg(json_build_object("
        "'point_id', p.id, 'name', p.name, 'rating', r.rating) order by rp.rank) "
        "filter (where rp.point_id is not null), '[]') "
        "from recommendation_attempts a "
        "left join recommendation_points rp on rp.attempt_id = a.id "
        "left join points p on p.id = rp.point_id "
        "left join point_ratings r on r.attempt_id = rp.attempt_id and r.point_id = rp.point_id "
        "where a.user_id = %s and a.outcome = any(%s) "
        "group by a.id order by a.created_at desc, a.id desc limit %s offset %s",
        (user_id, VISIBLE_OUTCOMES, limit + 1, offset),
    ).fetchall()
    items = [
        HistoryItem(attempt_id=r[0], created_at=r[1], symptom=r[2], outcome=r[3], points=r[4])
        for r in rows[:limit]
    ]
    return HistoryPage(items=items, has_more=len(rows) > limit)


def get_history_detail(
    conn: psycopg.Connection, user_id: uuid.UUID, attempt_id: uuid.UUID
) -> HistoryDetail:
    row = conn.execute(
        "select created_at, symptom_text, outcome, clarification_question, clarification_answer "
        "from recommendation_attempts where id = %s and user_id = %s and outcome = any(%s)",
        (attempt_id, user_id, VISIBLE_OUTCOMES),
    ).fetchone()
    if row is None:
        raise NOT_FOUND
    created_at, symptom, outcome, question, answer = row

    ranked = conn.execute(
        "select rp.point_id, r.rating from recommendation_points rp "
        "left join point_ratings r on r.attempt_id = rp.attempt_id and r.point_id = rp.point_id "
        "where rp.attempt_id = %s order by rp.rank",
        (attempt_id,),
    ).fetchall()
    ratings = {pid: rating for pid, rating in ranked}
    records = get_points(conn, list(ratings))
    points = [
        RatedPoint(**point.model_dump(), rating=ratings[point.point_id])
        for point in build_points(
            [records[pid] for pid in ratings], get_settings().supabase_public_url
        )
    ]
    return HistoryDetail(
        attempt_id=attempt_id,
        created_at=created_at,
        symptom=symptom,
        outcome=outcome,
        clarification_question=question,
        clarification_answer=answer,
        points=points,
    )
