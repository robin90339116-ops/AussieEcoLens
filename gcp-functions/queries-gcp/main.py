from __future__ import annotations

import os
from typing import Any

import functions_framework
from flask import Request, jsonify, make_response

from db_access import query_by_species, query_by_tag_counts
from jwt_auth import with_cognito_auth


def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": os.getenv("CORS_ALLOW_ORIGIN", "*"),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
    }


def _json_response(body: Any, status: int = 200):
    response = make_response(jsonify(body), status)
    for key, value in _cors_headers().items():
        response.headers[key] = value
    return response


def _handle_options():
    response = make_response("", 204)
    for key, value in _cors_headers().items():
        response.headers[key] = value
    return response


def _request_json(request: Request) -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _owner_id(request: Request, body: dict[str, Any]) -> str | None:
    if body.get("owner_id"):
        return body["owner_id"]
    claims = getattr(request, "user_claims", {}) or {}
    return claims.get("sub") or claims.get("email")


@functions_framework.http
@with_cognito_auth
def q1_query_by_tags(request: Request):
    if request.method == "OPTIONS":
        return _handle_options()

    body = _request_json(request)
    tags = body.get("tags") or body.get("required_tags")
    if not isinstance(tags, dict) or not tags:
        return _json_response({"error": "tags must be a non-empty object, e.g. {'wombat': 2}"}, 400)

    try:
        limit = int(body.get("limit", 100))
    except (TypeError, ValueError):
        return _json_response({"error": "limit must be an integer"}, 400)

    items = query_by_tag_counts(tags, owner_id=_owner_id(request, body), limit=limit)
    return _json_response(
        {
            "query_type": "Q1_AND_TAG_COUNTS",
            "logic": "AND",
            "count": len(items),
            "items": items,
        }
    )


@functions_framework.http
@with_cognito_auth
def q2_query_by_species(request: Request):
    if request.method == "OPTIONS":
        return _handle_options()

    body = _request_json(request)
    species = request.args.get("species") or body.get("species")
    if not species:
        return _json_response({"error": "species is required"}, 400)

    try:
        limit = int(body.get("limit", request.args.get("limit", 100)))
    except (TypeError, ValueError):
        return _json_response({"error": "limit must be an integer"}, 400)

    items = query_by_species(species, owner_id=_owner_id(request, body), limit=limit)
    return _json_response(
        {
            "query_type": "Q2_SPECIES_EXISTS",
            "species": species,
            "count": len(items),
            "items": items,
        }
    )

