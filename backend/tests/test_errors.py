import logging

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.errors import install_error_handling
from app.main import app as main_app

SECRET = "invented symptom text that must stay private"


def make_app() -> FastAPI:
    app = FastAPI()
    install_error_handling(app)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET)

    return app


def test_unexpected_exception_returns_generic_error_without_details(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.ERROR)
    # The default TestClient re-raises anything the app lets through to the server (which
    # would log the message), so getting a response shows the exception was fully handled.
    response = TestClient(make_app()).get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_error",
            "message": "Something went wrong. Please try again.",
            "retryable": True,
        }
    }
    assert SECRET not in response.text
    assert "Traceback" not in response.text
    # Logged for diagnosis (class, route, stack) but without the exception message.
    assert "unhandled RuntimeError on GET /boom" in caplog.text
    assert "test_errors.py" in caplog.text
    assert SECRET not in caplog.text


def test_cors_headers_are_added_to_unexpected_errors() -> None:
    app = make_app()
    app.add_middleware(CORSMiddleware, allow_origins=["https://app.example.test"])
    response = TestClient(app).get("/boom", headers={"Origin": "https://app.example.test"})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "https://app.example.test"


def test_unknown_route_uses_common_shape() -> None:
    response = TestClient(main_app).get("/api/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_common_shape() -> None:
    response = TestClient(main_app).delete("/api/health")
    assert response.status_code == 405
    assert set(response.json()["error"]) == {"code", "message", "retryable"}
