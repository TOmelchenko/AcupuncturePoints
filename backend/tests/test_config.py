import pytest

from app.config import cors_origins


def test_no_cors_origins_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("FRONTEND_HOST", raising=False)
    assert cors_origins() == []


def test_cors_origins_from_list_and_frontend_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://a.example/, http://localhost:5173")
    monkeypatch.setenv("FRONTEND_HOST", "acupressure-web.onrender.com")
    assert cors_origins() == [
        "https://a.example",
        "http://localhost:5173",
        "https://acupressure-web.onrender.com",
    ]
