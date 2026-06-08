"""AWS Lambda container handler for wildlife species tagging."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from ecolens_core import (
    DEFAULT_LABELS_PATH,
    DEFAULT_MD_MODEL_PATH,
    DEFAULT_SPECIES_MODEL_PATH,
    build_metadata_record,
    error_response,
    file_type_from_key,
    parse_s3_event,
    public_s3_url,
    tag_image,
    tag_video,
)


MD_MODEL_PATH = Path(os.getenv("MD_MODEL_PATH", str(DEFAULT_MD_MODEL_PATH)))
SPECIES_MODEL_PATH = Path(os.getenv("SPECIES_MODEL_PATH", str(DEFAULT_SPECIES_MODEL_PATH)))
LABELS_PATH = Path(os.getenv("LABELS_PATH", str(DEFAULT_LABELS_PATH)))
THUMBNAIL_BUCKET = os.getenv("THUMBNAIL_BUCKET")
THUMBNAIL_PREFIX = os.getenv("THUMBNAIL_PREFIX", "thumbnails/")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE")
METADATA_API_URL = os.getenv("METADATA_API_URL")

MODEL_CACHE: dict[str, Any] = {}


def _s3_client():
    import boto3

    return boto3.client("s3")


def _dynamodb_table():
    import boto3

    if not DYNAMODB_TABLE:
        return None
    return boto3.resource("dynamodb").Table(DYNAMODB_TABLE)


def thumbnail_url_for(bucket: str, key: str, provided_url: str | None = None) -> str | None:
    if provided_url:
        return provided_url
    if file_type_from_key(key) != "image":
        return None
    thumb_bucket = THUMBNAIL_BUCKET or bucket
    thumb_key = f"{THUMBNAIL_PREFIX.rstrip('/')}/{Path(key).stem}.jpg"
    return public_s3_url(thumb_bucket, thumb_key)


def persist_metadata(record: dict[str, Any]) -> None:
    """Optionally persist metadata if D module provides a table or API endpoint."""
    table = _dynamodb_table()
    if table is not None:
        table.put_item(Item=record)

    if METADATA_API_URL:
        body = json.dumps(record).encode("utf-8")
        request = Request(
            METADATA_API_URL,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10) as response:
            response.read()


def process_local_file(
    local_path: str | Path,
    *,
    bucket: str,
    key: str,
    checksum: str | None = None,
    original_url: str | None = None,
    thumbnail_url: str | None = None,
    persist: bool = False,
) -> dict[str, Any]:
    file_type = file_type_from_key(key)
    if file_type == "unsupported":
        return error_response("UnsupportedFileType", "Only image and video files are supported", bucket, key)

    with tempfile.TemporaryDirectory(prefix="ecolens-ml-") as tmp:
        if file_type == "image":
            ml_result = tag_image(
                local_path,
                md_model_path=MD_MODEL_PATH,
                species_model_path=SPECIES_MODEL_PATH,
                labels_path=LABELS_PATH,
                work_dir=Path(tmp),
                model_cache=MODEL_CACHE,
            )
        else:
            ml_result = tag_video(
                local_path,
                work_dir=Path(tmp),
                md_model_path=MD_MODEL_PATH,
                species_model_path=SPECIES_MODEL_PATH,
                labels_path=LABELS_PATH,
                model_cache=MODEL_CACHE,
            )

    record = build_metadata_record(
        bucket=bucket,
        key=key,
        tags=ml_result["tags"],
        predictions=ml_result["predictions"],
        checksum=checksum,
        original_url=original_url,
        thumbnail_url=thumbnail_url_for(bucket, key, thumbnail_url),
    )

    if file_type == "video":
        record["frames_processed"] = ml_result.get("frames_processed", 0)
    else:
        record["detections"] = ml_result.get("detections", 0)

    if persist:
        persist_metadata(record)
        record["persisted"] = True
    else:
        record["persisted"] = False

    return record


def process_s3_object(record: dict[str, str | None]) -> dict[str, Any]:
    bucket = record["bucket"]
    key = record["key"]
    if bucket is None or key is None:
        return error_response("InvalidEvent", "Missing S3 bucket or key")

    file_type = file_type_from_key(key)
    if file_type == "unsupported":
        return error_response("UnsupportedFileType", "Only image and video files are supported", bucket, key)

    s3 = _s3_client()
    with tempfile.TemporaryDirectory(prefix="ecolens-object-") as tmp:
        local_path = Path(tmp) / Path(key).name
        s3.download_file(bucket, key, str(local_path))
        return process_local_file(
            local_path,
            bucket=bucket,
            key=key,
            checksum=record.get("checksum"),
            original_url=record.get("original_url"),
            thumbnail_url=record.get("thumbnail_url"),
            persist=bool(DYNAMODB_TABLE or METADATA_API_URL),
        )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    results = []
    for record in parse_s3_event(event):
        try:
            results.append(process_s3_object(record))
        except Exception as exc:
            results.append(error_response(type(exc).__name__, str(exc), record.get("bucket"), record.get("key")))

    return {
        "status": "ok" if all(item.get("status") == "ok" for item in results) else "partial_error",
        "results": results,
    }
