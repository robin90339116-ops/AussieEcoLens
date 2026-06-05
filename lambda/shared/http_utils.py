from __future__ import annotations

import base64
import json
import os
from typing import Any


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": os.getenv("CORS_ALLOW_ORIGIN", "*"),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST,DELETE",
    }


def response(status_code: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", **cors_headers()},
        "body": json.dumps(body, ensure_ascii=False),
    }


def parse_json_body(event: dict[str, Any]) -> dict[str, Any]:
    body = event.get("body")
    if not body:
        return {}
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")
    if isinstance(body, dict):
        return body
    return json.loads(body)


def query_params(event: dict[str, Any]) -> dict[str, Any]:
    return event.get("queryStringParameters") or {}


def current_user(event: dict[str, Any]) -> str | None:
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    if not claims:
        claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    return claims.get("sub") or claims.get("email")

