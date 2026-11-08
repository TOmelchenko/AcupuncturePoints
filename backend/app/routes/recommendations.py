import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth import CurrentUser, get_current_user
from app.errors import ApiError, error_responses
from app.schemas import (
    ClarificationRequest,
    FeedbackRequest,
    FeedbackResponse,
    RecommendationRequest,
    RecommendationResponse,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

User = Annotated[CurrentUser, Depends(get_current_user)]
NOT_IMPLEMENTED = ApiError(501, "not_implemented", "This feature is not available yet.")


@router.post(
    "",
    response_model=RecommendationResponse,
    summary="Submit a symptom",
    description="Returns three recommended points, a clarifying question, or a no-match result. "
    "Technical or AI failures return 502 `recommendation_failed` with `retryable: true`.",
    responses=error_responses(401, 422, 502),
)
def create_recommendation(body: RecommendationRequest, user: User) -> RecommendationResponse:
    raise NOT_IMPLEMENTED


@router.post(
    "/{attempt_id}/clarification",
    response_model=RecommendationResponse,
    summary="Answer a clarifying question",
    description="Continues an attempt that returned `clarification_needed`.",
    responses=error_responses(401, 404, 422, 502),
)
def answer_clarification(
    attempt_id: uuid.UUID, body: ClarificationRequest, user: User
) -> RecommendationResponse:
    raise NOT_IMPLEMENTED


@router.post(
    "/{attempt_id}/points/{point_id}/feedback",
    response_model=FeedbackResponse,
    summary="Rate a recommended point",
    description="Stores a 1–5 star rating for one point of the user's recommendation set. "
    "Rating the same point again replaces the earlier rating.",
    responses=error_responses(401, 404, 422),
)
def submit_feedback(
    attempt_id: uuid.UUID, point_id: str, body: FeedbackRequest, user: User
) -> FeedbackResponse:
    raise NOT_IMPLEMENTED
