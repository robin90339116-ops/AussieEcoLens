from __future__ import annotations

import os
from typing import Any

import functions_framework
from flask import Request, jsonify, make_response

from db_access import query_by_species, query_by_tag_counts
from jwt_auth import with_cognito_auth


def _allowed_origin(request: Request | None = None) -> str:
    configured = os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:3000")
    allowed = [origin.strip() for origin in configured.split(",") if origin.strip()]
    if "*" in allowed:
        return "*"
    request_origin = request.headers.get("Origin") if request else None
    if request_origin and request_origin in allowed:
        return request_origin
    return allowed[0] if allowed else "http://localhost:3000"


def _cors_headers(request: Request | None = None) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": _allowed_origin(request),
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,GET,POST",
    }


def _json_response(body: Any, status: int = 200, request: Request | None = None):
    response = make_response(jsonify(body), status)
    for key, value in _cors_headers(request).items():
        response.headers[key] = value
    return response


def _handle_options(request: Request):
    response = make_response("", 204)
    for key, value in _cors_headers(request).items():
        response.headers[key] = value
    return response


def _request_json(request: Request) -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@functions_framework.http
@with_cognito_auth
def q1_query_by_tags(request: Request):
    if request.method == "OPTIONS":
        return _handle_options(request)

    body = _request_json(request)
    tags = body.get("tags") or body.get("required_tags")
    if not isinstance(tags, dict) or not tags:
        return _json_response({"error": "tags must be a non-empty object, e.g. {'wombat': 2}"}, 400, request)

    try:
        limit = int(body.get("limit", 100))
    except (TypeError, ValueError):
        return _json_response({"error": "limit must be an integer"}, 400, request)

    # Authentication is required, but Q1 searches the shared wildlife database.
    # Do not filter by Cognito user; the assignment expects all matching files.
    items = query_by_tag_counts(tags, limit=limit)
    return _json_response(
        {
            "query_type": "Q1_AND_TAG_COUNTS",
            "logic": "AND",
            "count": len(items),
            "items": items,
        },
        request=request,
    )


@functions_framework.http
@with_cognito_auth
def q2_query_by_species(request: Request):
    if request.method == "OPTIONS":
        return _handle_options(request)

    body = _request_json(request)
    species = request.args.get("species") or body.get("species")
    if not species:
        return _json_response({"error": "species is required"}, 400, request)

    try:
        limit = int(body.get("limit", request.args.get("limit", 100)))
    except (TypeError, ValueError):
        return _json_response({"error": "limit must be an integer"}, 400, request)

    # Authentication is required, but Q2 searches the shared wildlife database.
    # Do not filter by Cognito user; the assignment expects all matching files.
    items = query_by_species(species, limit=limit)
    return _json_response(
        {
            "query_type": "Q2_SPECIES_EXISTS",
            "species": species,
            "count": len(items),
            "items": items,
        },
        request=request,
    )
