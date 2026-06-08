from __future__ import annotations

import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from aussie_ecolens_db import attach_presigned_media_urls, get_by_thumbnail_url
from http_utils import parse_json_body, query_params, response


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    params = query_params(event)
    body = parse_json_body(event)
    thumbnail_url = params.get("thumbnail_url") or body.get("thumbnail_url")

    if not thumbnail_url:
        return response(400, {"error": "thumbnail_url is required"})

    item = get_by_thumbnail_url(thumbnail_url)
    if not item:
        return response(404, {"error": "file_not_found"})

    item = attach_presigned_media_urls(item)
    return response(
        200,
        {
            "file_id": item["file_id"],
            "thumbnail_url": item.get("thumbnail_url"),
            "thumbnail_access_url": item.get("thumbnail_access_url"),
            "thumbnail_raw_url": item.get("thumbnail_raw_url"),
            "original_url": item.get("original_url"),
            "original_access_url": item.get("original_access_url"),
            "original_raw_url": item.get("original_raw_url"),
            "tags": item.get("tags", {}),
            "type": item.get("type"),
        },
    )
