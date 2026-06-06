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
    return boto3.client("s3", region_name=os.getenv("AWS_REGION", "us-east-1"))


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


def _delete_one(*, file_id: str | None = None, url: str | None = None) -> dict:
    item = get_by_file_id(file_id) if file_id else get_by_url(url)
    if not item:
        return {"target": file_id or url, "error": "file_not_found"}

    deleted_objects = _delete_media_objects(item)
    deleted_record = delete_record(file_id=item["file_id"])

    return {
        "deleted_file_id": item["file_id"],
        "deleted_s3_objects": deleted_objects,
        "deleted_record": deleted_record,
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    body = parse_json_body(event)
    targets: list[dict[str, str]] = []

    file_ids = body.get("file_ids")
    urls = body.get("urls")
    if isinstance(file_ids, list):
        targets.extend({"file_id": item} for item in file_ids if item)
    if isinstance(urls, list):
        targets.extend({"url": item} for item in urls if item)

    file_id = body.get("file_id")
    url = body.get("url") or body.get("original_url") or body.get("thumbnail_url")
    if file_id:
        targets.append({"file_id": file_id})
    if url:
        targets.append({"url": url})

    if not targets:
        return response(400, {"error": "file_id, file_ids, url, or urls is required"})

    deleted: list[dict] = []
    errors: list[dict] = []
    for target in targets:
        try:
            result = _delete_one(file_id=target.get("file_id"), url=target.get("url"))
        except Exception as exc:
            errors.append({"target": target.get("file_id") or target.get("url"), "error": str(exc)})
            continue
        if result.get("error"):
            errors.append(result)
        else:
            deleted.append(result)

    status = 207 if deleted and errors else 404 if errors and not deleted else 200
    return response(status, {"deleted": deleted, "errors": errors})
