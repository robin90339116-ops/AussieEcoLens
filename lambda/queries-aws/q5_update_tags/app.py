from __future__ import annotations

import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from aussie_ecolens_db import update_tags
from http_utils import parse_json_body, response


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    body = parse_json_body(event)
    urls = body.get("urls")
    tags = body.get("tags")
    operation = body.get("operation")

    if not isinstance(urls, list) or not urls:
        return response(400, {"error": "urls must be a non-empty list"})
    if not tags:
        return response(400, {"error": "tags is required"})
    if operation is None:
        return response(400, {"error": "operation is required: add/1 or remove/0"})

    try:
        result = update_tags(urls=urls, tags=tags, operation=operation)
    except ValueError as exc:
        return response(400, {"error": str(exc)})

    status = 207 if result["errors"] else 200
    return response(status, result)
