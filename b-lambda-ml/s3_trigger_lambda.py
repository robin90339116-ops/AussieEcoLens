"""Lightweight AWS Lambda triggered by S3 ObjectCreated events (Route B).

This function is deliberately small. It does NOT run the ML model. Instead it:
1. Receives the S3 upload event (serverless trigger requirement satisfied here).
2. Generates a short-lived presigned GET URL for the uploaded object.
3. Calls the OCI ML inference service (`ml_service.py`) over HTTPS, passing the
   bearer token so the cross-cloud request is authorised.
4. Returns the metadata produced by the OCI service.

This keeps Cognito/S3/trigger on AWS, while the heavy PyTorch inference runs on the
Oracle Cloud instance. It avoids packaging large models into AWS Lambda and avoids
AWS Academy container/role limitations.

Environment variables:
- OCI_ML_ENDPOINT   : e.g. https://<oci-host>/v1/tag/s3
- OCI_API_TOKEN     : bearer token expected by the OCI service (API_AUTH_TOKEN there)
- PRESIGN_EXPIRY    : presigned URL TTL in seconds (default 600)
- REQUEST_TIMEOUT   : HTTP timeout to the OCI service (default 300)
"""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

OCI_ML_ENDPOINT = os.getenv("OCI_ML_ENDPOINT")
OCI_API_TOKEN = os.getenv("OCI_API_TOKEN")
PRESIGN_EXPIRY = int(os.getenv("PRESIGN_EXPIRY", "600"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def _s3_client():
    import boto3

    return boto3.client("s3")


def _parse_records(event: dict[str, Any]) -> list[dict[str, str]]:
    if "Records" not in event:
        return [{"bucket": event["bucket"], "key": event["key"]}]
    records = []
    for record in event["Records"]:
        s3 = record["s3"]
        records.append(
            {
                "bucket": s3["bucket"]["name"],
                "key": s3["object"]["key"].replace("+", " "),
            }
        )
    return records


def _is_supported(key: str) -> bool:
    lower = key.lower()
    return any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS)


def _call_oci(bucket: str, key: str, presigned_url: str) -> dict[str, Any]:
    if not OCI_ML_ENDPOINT:
        raise RuntimeError("OCI_ML_ENDPOINT is not configured")

    payload = json.dumps(
        {
            "bucket": bucket,
            "key": key,
            "image_url": presigned_url,
            "original_url": f"https://{bucket}.s3.amazonaws.com/{key}",
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if OCI_API_TOKEN:
        headers["Authorization"] = f"Bearer {OCI_API_TOKEN}"

    request = Request(OCI_ML_ENDPOINT, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    s3 = _s3_client()
    results = []
    for record in _parse_records(event):
        bucket, key = record["bucket"], record["key"]
        if not _is_supported(key):
            results.append({"status": "skipped", "bucket": bucket, "key": key, "reason": "unsupported file type"})
            continue
        try:
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=PRESIGN_EXPIRY,
            )
            results.append(_call_oci(bucket, key, presigned_url))
        except Exception as exc:
            results.append({"status": "error", "error_type": type(exc).__name__, "message": str(exc), "bucket": bucket, "key": key})

    return {
        "status": "ok" if all(r.get("status") in ("ok", "skipped") for r in results) else "partial_error",
        "results": results,
    }
