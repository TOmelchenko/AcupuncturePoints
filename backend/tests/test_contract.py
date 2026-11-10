"""The API contract: request validation, response models and the OpenAPI document."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from app.auth import CurrentUser, get_current_user
from app.main import app
from app.schemas import (
    FeedbackRequest,
    RecommendationRequest,
    RecommendationResponse,
    RecommendedPoint,
)

POINT = {
    "point_id": "LI4",
    "rank": 1,
    "name": "Hegu",
    "location_text": "Between thumb and finger.",
    "instructions": ["Press firmly."],
}


@pytest.fixture
def client() -> Any:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(uuid.uuid4(), None)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_symptom_is_stripped_and_length_checked() -> None:
    assert RecommendationRequest(symptom="  sore neck  ").symptom == "sore neck"
    for bad in ["", "  a ", "x" * 1001]:
        with pytest.raises(ValidationError):
            RecommendationRequest(symptom=bad)


def test_unknown_request_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RecommendationRequest.model_validate({"symptom": "sore neck", "user_id": "x"})


@pytest.mark.parametrize("rating", [0, 6, 2.5])
def test_rating_must_be_whole_number_1_to_5(rating: float) -> None:
    with pytest.raises(ValidationError):
        FeedbackRequest.model_validate({"rating": rating})


def test_optional_point_details_default_to_absent() -> None:
    point = RecommendedPoint.model_validate(POINT)
    assert (point.image_url, point.duration, point.pressure) == (None, None, None)


def test_recommendation_set_needs_exactly_three_points() -> None:
    adapter: TypeAdapter[Any] = TypeAdapter(RecommendationResponse)
    attempt = str(uuid.uuid4())
    points = [{**POINT, "rank": r, "point_id": f"P{r}"} for r in (1, 2, 3)]
    assert adapter.validate_python(
        {"outcome": "recommended", "attempt_id": attempt, "points": points}
    )
    with pytest.raises(ValidationError):
        adapter.validate_python(
            {"outcome": "recommended", "attempt_id": attempt, "points": points[:2]}
        )


def test_response_union_is_selected_by_outcome() -> None:
    adapter: TypeAdapter[Any] = TypeAdapter(RecommendationResponse)
    attempt = str(uuid.uuid4())
    question = adapter.validate_python(
        {"outcome": "clarification_needed", "attempt_id": attempt, "question": "Where?"}
    )
    assert type(question).__name__ == "ClarificationNeeded"
    no_match = adapter.validate_python(
        {"outcome": "no_match", "attempt_id": attempt, "message": "x"}
    )
    assert type(no_match).__name__ == "NoMatch"


def test_invalid_request_returns_common_error_shape(client: TestClient) -> None:
    response = client.post("/api/recommendations", json={"symptom": ""})
    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "validation_error",
            "message": "Please check your input and try again.",
            "retryable": False,
        }
    }


def test_endpoints_require_authentication() -> None:
    attempt = uuid.uuid4()
    for path, body in [
        ("/api/recommendations", {"symptom": "sore neck"}),
        (f"/api/recommendations/{attempt}/clarification", {"answer": "left side"}),
        (f"/api/recommendations/{attempt}/points/LI4/feedback", {"rating": 4}),
    ]:
        response = TestClient(app).post(path, json=body)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"
    for path in ["/api/recommendations", f"/api/recommendations/{attempt}"]:
        response = TestClient(app).get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize("query", ["limit=0", "limit=51", "offset=-1", "limit=x"])
def test_history_paging_is_validated(client: TestClient, query: str) -> None:
    response = client.get(f"/api/recommendations?{query}")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_openapi_documents_the_contract() -> None:
    spec = TestClient(app).get("/openapi.json").json()
    paths = spec["paths"]

    create = paths["/api/recommendations"]["post"]
    assert create["requestBody"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RecommendationRequest"
    )
    ok_schema = create["responses"]["200"]["content"]["application/json"]["schema"]
    assert ok_schema["discriminator"]["propertyName"] == "outcome"
    for status in ("401", "422", "502"):
        assert create["responses"][status]["content"]["application/json"]["schema"][
            "$ref"
        ].endswith("/ErrorResponse")

    assert "/api/recommendations/{attempt_id}/clarification" in paths
    feedback = paths["/api/recommendations/{attempt_id}/points/{point_id}/feedback"]["post"]
    assert {p["name"] for p in feedback["parameters"]} == {"attempt_id", "point_id"}

    point = spec["components"]["schemas"]["RecommendedPoint"]
    assert {"image_url", "location_text", "duration", "pressure"} <= set(point["properties"])
    assert set(point["required"]) == {"point_id", "rank", "name", "location_text", "instructions"}
