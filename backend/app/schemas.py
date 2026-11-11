"""Request and response models: the API contract shared with the frontend.

FastAPI turns these into the OpenAPI document at /docs and /openapi.json.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# psycopg rejects NUL characters, so they are refused here (422) rather than failing on insert.
NO_NUL = r"^[^\x00]*$"
SymptomText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000, pattern=NO_NUL)
]
AnswerText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000, pattern=NO_NUL)
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- Requests ----------------------------------------------------------------


class RecommendationRequest(StrictModel):
    symptom: SymptomText = Field(description="The symptom in the user's own words (English).")


class ClarificationRequest(StrictModel):
    answer: AnswerText = Field(description="The user's answer to the clarifying question.")


class FeedbackRequest(StrictModel):
    rating: int = Field(ge=1, le=5, description="How helpful the point was, 1–5 stars.")


# --- Responses ---------------------------------------------------------------


class RecommendedPoint(BaseModel):
    point_id: str = Field(description="Curated point code, e.g. 'LI4'.")
    rank: int = Field(ge=1, le=3)
    name: str
    location_text: str = Field(description="Text location; shown when there is no image.")
    image_url: str | None = Field(default=None, description="Curated location image, if any.")
    image_attribution: str | None = None
    instructions: list[str] = Field(
        min_length=1, description="Ordered steps for applying pressure."
    )
    duration: str | None = Field(
        default=None, description="Only present when the source states it."
    )
    pressure: str | None = Field(
        default=None, description="Only present when the source states it."
    )


class RecommendationSet(BaseModel):
    outcome: Literal["recommended"] = "recommended"
    attempt_id: uuid.UUID
    points: list[RecommendedPoint] = Field(min_length=3, max_length=3)


class ClarificationNeeded(BaseModel):
    outcome: Literal["clarification_needed"] = "clarification_needed"
    attempt_id: uuid.UUID
    question: str


class NoMatch(BaseModel):
    outcome: Literal["no_match"] = "no_match"
    attempt_id: uuid.UUID
    message: str


RecommendationResponse = Annotated[
    RecommendationSet | ClarificationNeeded | NoMatch, Field(discriminator="outcome")
]


class FeedbackResponse(BaseModel):
    attempt_id: uuid.UUID
    point_id: str
    rating: int


# --- History -------------------------------------------------------------------

HistoryOutcome = Literal["recommended", "clarification_needed", "no_match"]


class HistoryPointSummary(BaseModel):
    point_id: str
    name: str
    rating: int | None = Field(description="The user's 1–5 rating, if given.")


class HistoryItem(BaseModel):
    attempt_id: uuid.UUID
    created_at: datetime
    symptom: str = Field(description="The symptom text as the user entered it.")
    outcome: HistoryOutcome
    points: list[HistoryPointSummary] = Field(
        description="The recommended points, best first; empty unless outcome is 'recommended'."
    )


class HistoryPage(BaseModel):
    items: list[HistoryItem]
    has_more: bool


class RatedPoint(RecommendedPoint):
    rating: int | None = Field(description="The user's 1–5 rating, if given.")


class HistoryDetail(BaseModel):
    attempt_id: uuid.UUID
    created_at: datetime
    symptom: str
    outcome: HistoryOutcome
    clarification_question: str | None
    clarification_answer: str | None
    points: list[RatedPoint] = Field(description="Empty unless outcome is 'recommended'.")


class ErrorBody(BaseModel):
    code: Literal[
        "unauthorized",
        "validation_error",
        "not_found",
        "recommendation_failed",
        "rate_limited",
        "not_implemented",
        "internal_error",
    ]
    message: str = Field(description="Generic message that is safe to show to the user.")
    retryable: bool = False


class ErrorResponse(BaseModel):
    error: ErrorBody
