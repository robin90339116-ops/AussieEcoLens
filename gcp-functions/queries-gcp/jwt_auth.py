from __future__ import annotations

import os
import time
from functools import wraps
from typing import Any, Callable

import jwt
import requests
from jwt import PyJWKClient


_JWKS_CLIENT: PyJWKClient | None = None
_JWKS_CREATED_AT = 0.0


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "true").lower() not in {"0", "false", "no"}


def _issuer() -> str:
    region = os.getenv("COGNITO_REGION") or os.getenv("AWS_REGION", "ap-southeast-2")
    pool_id = os.getenv("COGNITO_USER_POOL_ID")
    if not pool_id:
        raise RuntimeError("COGNITO_USER_POOL_ID is not configured")
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"


def _jwk_client() -> PyJWKClient:
    global _JWKS_CLIENT, _JWKS_CREATED_AT
    if _JWKS_CLIENT and time.time() - _JWKS_CREATED_AT < 3600:
        return _JWKS_CLIENT
    _JWKS_CLIENT = PyJWKClient(f"{_issuer()}/.well-known/jwks.json")
    _JWKS_CREATED_AT = time.time()
    return _JWKS_CLIENT


def verify_bearer_token(auth_header: str | None) -> dict[str, Any]:
    if not auth_header or not auth_header.startswith("Bearer "):
        raise PermissionError("missing bearer token")

    token = auth_header.removeprefix("Bearer ").strip()
    signing_key = _jwk_client().get_signing_key_from_jwt(token)
    audience = os.getenv("COGNITO_APP_CLIENT_ID")
    options = {"verify_aud": bool(audience)}

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=audience,
        issuer=_issuer(),
        options=options,
    )


def with_cognito_auth(handler: Callable):
    @wraps(handler)
    def wrapped(request):
        if getattr(request, "method", "") == "OPTIONS":
            return handler(request)

        if not auth_required():
            request.user_claims = {}
            return handler(request)

        try:
            request.user_claims = verify_bearer_token(request.headers.get("Authorization"))
        except (PermissionError, jwt.InvalidTokenError, requests.RequestException, RuntimeError) as exc:
            return {"error": "unauthorized", "detail": str(exc)}, 401
        return handler(request)

    return wrapped
