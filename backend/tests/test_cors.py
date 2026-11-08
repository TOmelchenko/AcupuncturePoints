"""CORS is configured from settings at startup; check it on a freshly imported app."""

import importlib

import pytest
from fastapi.testclient import TestClient

import app.main
from app.config import get_settings


def test_allowed_origin_gets_cors_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_HOST", "web.example")
    get_settings.cache_clear()
    try:
        module = importlib.reload(app.main)
        client = TestClient(module.app)
        preflight = client.options(
            "/api/recommendations",
            headers={
                "Origin": "https://web.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert preflight.headers["access-control-allow-origin"] == "https://web.example"
        other = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert "access-control-allow-origin" not in other.headers
    finally:
        monkeypatch.delenv("FRONTEND_HOST")
        get_settings.cache_clear()
        importlib.reload(app.main)
