"""AWS Lambda handler for image thumbnail generation."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from ecolens_core import (
    content_type_for_key,
    error_response,
    file_type_from_key,
    generate_thumbnail,
    parse_s3_event,
    public_s3_url,
)


THUMBNAIL_PREFIX = os.getenv("THUMBNAIL_PREFIX", "thumbnails/")
THUMBNAIL_BUCKET = os.getenv("THUMBNAIL_BUCKET")
MAX_THUMBNAIL_DIMENSION = int(os.getenv("MAX_THUMBNAIL_DIMENSION", "320"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "82"))


def _s3_client():
    import boto3

    return boto3.client("s3")


def thumbnail_key_for(original_key: str) -> str:
    stem = Path(original_key).stem
    return f"{THUMBNAIL_PREFIX.rstrip('/')}/{stem}.jpg"


def create_thumbnail_for_local_file(
    local_path: str | Path,
    output_path: str | Path,
    max_dimension: int = MAX_THUMBNAIL_DIMENSION,
    quality: int = JPEG_QUALITY,
) -> dict[str, Any]:
    return generate_thumbnail(local_path, output_path, max_dimension=max_dimension, quality=quality)


def process_s3_object(bucket: str, key: str) -> dict[str, Any]:
    if file_type_from_key(key) != "image":
        return error_response("UnsupportedFileType", "Thumbnail generation supports images only", bucket, key)

    thumbnail_bucket = THUMBNAIL_BUCKET or bucket
    thumbnail_key = thumbnail_key_for(key)
    s3 = _s3_client()

    with tempfile.TemporaryDirectory(prefix="ecolens-thumb-") as tmp:
        local_source = Path(tmp) / Path(key).name
        local_thumbnail = Path(tmp) / "thumbnail.jpg"
        s3.download_file(bucket, key, str(local_source))

        thumbnail_info = generate_thumbnail(
            local_source,
            local_thumbnail,
            max_dimension=MAX_THUMBNAIL_DIMENSION,
            quality=JPEG_QUALITY,
        )

        s3.upload_file(
            str(local_thumbnail),
            thumbnail_bucket,
            thumbnail_key,
            ExtraArgs={
                "ContentType": content_type_for_key(thumbnail_key),
            },
        )

    return {
        "status": "ok",
        "bucket": bucket,
        "key": key,
        "thumbnail_bucket": thumbnail_bucket,
        "thumbnail_key": thumbnail_key,
        "thumbnail_url": public_s3_url(thumbnail_bucket, thumbnail_key),
        "width": thumbnail_info["width"],
        "height": thumbnail_info["height"],
        "content_type": thumbnail_info["content_type"],
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    results = []
    for record in parse_s3_event(event):
        try:
            results.append(process_s3_object(record["bucket"], record["key"]))
        except Exception as exc:
            results.append(error_response(type(exc).__name__, str(exc), record.get("bucket"), record.get("key")))

    return {
        "status": "ok" if all(item.get("status") == "ok" for item in results) else "partial_error",
        "results": results,
    }
