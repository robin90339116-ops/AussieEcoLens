from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

import boto3

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from aussie_ecolens_db import delete_record, get_by_file_id, get_by_url
from http_utils import parse_json_body, response


def _s3_client():
    return boto3.client("s3", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))


def _key_from_url(url: str) -> tuple[str | None, str | None]:
    if not url:
        return None, None
    parsed = urlparse(url)
    host = parsed.netloc
    path = unquote(parsed.path.lstrip("/"))

    if ".s3." in host or host.endswith(".amazonaws.com"):
        bucket = host.split(".s3.")[0]
        return bucket, path
    if host.startswith("s3.") or host == "s3.amazonaws.com":
        parts = path.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
    return None, None


def _delete_object(bucket: str | None, key: str | None) -> dict[str, str] | None:
    if not bucket or not key:
        return None
    _s3_client().delete_object(Bucket=bucket, Key=key)
    return {"bucket": bucket, "key": key}


def _delete_media_objects(item: dict) -> list[dict[str, str]]:
    deleted: list[dict[str, str]] = []

    original_bucket = os.getenv("ORIGINAL_BUCKET")
    thumbnail_bucket = os.getenv("THUMBNAIL_BUCKET")

    original_key = item.get("original_s3_key")
    thumbnail_key = item.get("thumbnail_s3_key")

    if original_key:
        deleted_item = _delete_object(original_bucket, original_key)
        if deleted_item:
            deleted.append(deleted_item)
    else:
        bucket, key = _key_from_url(item.get("original_url", ""))
        deleted_item = _delete_object(bucket, key)
        if deleted_item:
            deleted.append(deleted_item)

    if thumbnail_key:
        deleted_item = _delete_object(thumbnail_bucket, thumbnail_key)
        if deleted_item:
            deleted.append(deleted_item)
    else:
        bucket, key = _key_from_url(item.get("thumbnail_url", ""))
        deleted_item = _delete_object(bucket, key)
        if deleted_item:
            deleted.append(deleted_item)

    return deleted


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    body = parse_json_body(event)
    file_id = body.get("file_id")
    url = body.get("url") or body.get("original_url") or body.get("thumbnail_url")

    if not file_id and not url:
        return response(400, {"error": "file_id or url is required"})

    item = get_by_file_id(file_id) if file_id else get_by_url(url)
    if not item:
        return response(404, {"error": "file_not_found"})

    deleted_objects = _delete_media_objects(item)
    deleted_record = delete_record(file_id=item["file_id"])

    return response(
        200,
        {
            "deleted_file_id": item["file_id"],
            "deleted_s3_objects": deleted_objects,
            "deleted_record": deleted_record,
        },
    )
