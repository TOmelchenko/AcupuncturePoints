import json
import os
import time
import urllib.request
import uuid
from collections.abc import Iterator
from typing import Annotated, Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import CurrentUser, TokenVerifier, get_current_user, get_token_verifier
from app.errors import ApiError, api_error_handler

KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_KEY = ec.generate_private_key(ec.SECP256R1())
USER_ID = uuid.uuid4()


class StaticJwkClient:
    """Stands in for PyJWKClient: always returns our test public key."""

    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK:
        return jwt.PyJWK.from_dict(
            json.loads(jwt.algorithms.ECAlgorithm.to_jwk(KEY.public_key())), "ES256"
        )


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(ApiError, api_error_handler)

    @app.get("/protected")
    def protected(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
        return {"id": str(user.id), "email": user.email}

    return app


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = make_app()
    app.dependency_overrides[get_token_verifier] = lambda: TokenVerifier(StaticJwkClient())  # type: ignore[arg-type]
    yield TestClient(app)


def token(key: Any = KEY, algorithm: str = "ES256", **overrides: Any) -> str:
    claims = {
        "sub": str(USER_ID),
        "aud": "authenticated",
        "email": "user@example.test",
        "exp": int(time.time()) + 600,
        **overrides,
    }
    return jwt.encode(claims, key, algorithm=algorithm)


def get(client: TestClient, auth: str | None) -> Any:
    headers = {"Authorization": auth} if auth else {}
    return client.get("/protected", headers=headers)


def assert_unauthorized(response: Any) -> None:
    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "unauthorized",
            "message": "Please sign in to continue.",
            "retryable": False,
        }
    }


def test_valid_token_gives_current_user(client: TestClient) -> None:
    response = get(client, f"Bearer {token()}")
    assert response.status_code == 200
    assert response.json() == {"id": str(USER_ID), "email": "user@example.test"}


def test_missing_token_is_rejected(client: TestClient) -> None:
    assert_unauthorized(get(client, None))


@pytest.mark.parametrize(
    "bad_token",
    [
        "not-a-jwt",
        token(exp=int(time.time()) - 10),  # expired
        token(aud="anon"),  # wrong audience
        token(key=OTHER_KEY),  # signed by another key
        token(sub="not-a-uuid"),  # malformed user id
        token(key="a-shared-secret-that-is-long-enough-for-hs256", algorithm="HS256"),
    ],
    ids=["garbage", "expired", "audience", "signature", "sub", "hs256"],
)
def test_invalid_tokens_are_rejected(client: TestClient, bad_token: str) -> None:
    assert_unauthorized(get(client, f"Bearer {bad_token}"))


def test_real_supabase_token_is_accepted() -> None:
    """End to end against local Supabase Auth (skipped when it is not running)."""
    supabase_url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    anon_key = os.environ.get("SUPABASE_ANON_KEY")
    if not (service_key and anon_key):
        if os.environ.get("REQUIRE_DB") == "1":
            pytest.fail("SUPABASE_SERVICE_ROLE_KEY and SUPABASE_ANON_KEY must be set")
        pytest.skip("Supabase keys not set")

    def call(path: str, key: str, body: dict[str, Any], method: str = "POST") -> Any:
        request = urllib.request.Request(
            f"{supabase_url}/auth/v1/{path}",
            method=method,
            data=json.dumps(body).encode(),
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            return json.loads(response.read() or b"{}")

    email, password = f"auth-test-{uuid.uuid4()}@example.test", "test-password-123"
    user = call(
        "admin/users", service_key, {"email": email, "password": password, "email_confirm": True}
    )
    try:
        session = call(
            "token?grant_type=password", anon_key, {"email": email, "password": password}
        )
        get_token_verifier.cache_clear()
        response = get(TestClient(make_app()), f"Bearer {session['access_token']}")
        assert response.status_code == 200
        assert response.json()["id"] == user["id"]
    finally:
        call(f"admin/users/{user['id']}", service_key, {}, method="DELETE")
