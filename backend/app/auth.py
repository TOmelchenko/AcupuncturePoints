"""Authentication: verify the Supabase access token sent by the frontend.

Supabase Auth signs access tokens with an asymmetric key and publishes the
public keys as a JWKS, so the backend needs no shared secret. We check the
signature, expiry and the `authenticated` audience; the user id is `sub`.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.errors import ApiError

ALGORITHMS = ["ES256", "RS256"]
AUDIENCE = "authenticated"


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str | None


class TokenVerifier:
    def __init__(self, jwk_client: jwt.PyJWKClient) -> None:
        self.jwk_client = jwk_client

    def verify(self, token: str) -> dict[str, Any]:
        """Return the token's claims, or raise jwt.PyJWTError if it is not valid."""
        signing_key = self.jwk_client.get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=ALGORITHMS,
            audience=AUDIENCE,
            options={"require": ["exp", "sub", "aud"]},
        )
        return claims


@lru_cache
def get_token_verifier() -> TokenVerifier:
    jwks_url = f"{get_settings().supabase_url}/auth/v1/.well-known/jwks.json"
    return TokenVerifier(jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600))


UNAUTHORIZED = ApiError(401, "unauthorized", "Please sign in to continue.")


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))
    ],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> CurrentUser:
    if credentials is None:
        raise UNAUTHORIZED
    try:
        claims = verifier.verify(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        raise UNAUTHORIZED from None
    return CurrentUser(id=user_id, email=claims.get("email"))
