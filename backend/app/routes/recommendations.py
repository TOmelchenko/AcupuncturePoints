import uuid
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends

from app.ai import AI, get_ai
from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.errors import error_responses
from app.feedback import save_rating
from app.recommender import Recommender
from app.schemas import (
    ClarificationRequest,
    FeedbackRequest,
    FeedbackResponse,
    RecommendationRequest,
    RecommendationResponse,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

User = Annotated[CurrentUser, Depends(get_current_user)]
Db = Annotated[psycopg.Connection, Depends(get_db)]
Ai = Annotated[AI, Depends(get_ai)]


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Submit a symptom",
    description="Returns three recommended points, a clarifying question, or a no-match result. "
    "Technical or AI failures return 502 `recommendation_failed` with `retryable: true`.",
    responses=error_responses(401, 422, 502),
)
def create_recommendation(
    body: RecommendationRequest, user: User, db: Db, ai: Ai
) -> RecommendationResponse:
    return Recommender(db, ai).start(user.id, body.symptom)


@router.post(
    "/{attempt_id}/clarification",
    response_model=RecommendationResponse,
    summary="Answer a clarifying question",
    description="Continues an attempt that returned `clarification_needed` (or failed after "
    "one, to retry). A weak match after clarification returns `no_match`.",
    responses=error_responses(401, 404, 422, 502),
)
def answer_clarification(
    attempt_id: uuid.UUID, body: ClarificationRequest, user: User, db: Db, ai: Ai
) -> RecommendationResponse:
    return Recommender(db, ai).clarify(user.id, attempt_id, body.answer)


@router.post(
    "/{attempt_id}/points/{point_id}/feedback",
    response_model=FeedbackResponse,
    summary="Rate a recommended point",
    description="Stores a 1–5 star rating for one point of the user's recommendation set. "
    "Rating the same point again replaces the earlier rating.",
    responses=error_responses(401, 404, 422),
)
def submit_feedback(
    attempt_id: uuid.UUID, point_id: str, body: FeedbackRequest, user: User, db: Db
) -> FeedbackResponse:
    return save_rating(db, user.id, attempt_id, point_id, body.rating)
