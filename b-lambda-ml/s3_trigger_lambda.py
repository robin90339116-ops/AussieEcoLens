"""Forwarding AWS Lambda triggered by S3 ObjectCreated events (Route B).

This is the SINGLE S3 notification target for the `uploads/` prefix (the "doorbell").
S3 only allows one notification target per bucket/event/prefix, so this Lambda fans
work out itself instead of having S3 trigger several Lambdas directly:

1. Receives the S3 upload event (the serverless trigger requirement is satisfied here).
2. Asynchronously invokes the thumbnail Lambda (InvocationType="Event") so the
   thumbnail is generated without blocking inference.
3. Generates a short-lived presigned GET URL for the uploaded object.
4. Calls the OCI ML inference service (`ml_service.py`) over HTTPS with the bearer
   token, so the heavy PyTorch inference runs on the Oracle Cloud instance.
5. Persists the returned metadata to DynamoDB (table `AussieEcoLensFiles`) using
   D's shared module `aussie_ecolens_db.write_record`, so detection results are no
   longer lost on the async return path.
6. Optionally triggers the new-file (tag-based) notification, because the table has
   no DynamoDB Stream and notifications must be published explicitly.

Environment variables
---------------------
- OCI_ML_ENDPOINT      : e.g. https://<oci-host>:8080/v1/tag/s3        (required)
- OCI_API_TOKEN        : bearer token expected by the OCI service (API_AUTH_TOKEN)
- PRESIGN_EXPIRY       : presigned URL TTL in seconds (default 600)
- REQUEST_TIMEOUT      : HTTP timeout to the OCI service (default 300)
- THUMBNAIL_LAMBDA_NAME: name/ARN of the thumbnail Lambda to async-invoke (optional)
- THUMBNAIL_PREFIX     : S3 prefix where thumbnails are stored (default thumbnails/)
- PERSIST_TO_DB        : "true"/"false" whether to write to DynamoDB (default true)
- DEFAULT_OWNER_ID     : owner_id fallback when none is found on the object
- OWNER_METADATA_KEY   : S3 user-metadata key carrying the owner (default owner-id)
- NOTIFY_LAMBDA_NAME   : name/ARN of D's notifications Lambda for publish (optional)

Packaging note
--------------
The deployment zip MUST include D's `lambda/shared/aussie_ecolens_db.py` (and its
boto3 dependency) so `write_record` is importable. See ORACLE_DEPLOYMENT.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

# D's shared persistence module. It is bundled into the deployment zip; guard the
# import so the file stays importable for local unit testing without boto3/D code.
try:  # pragma: no cover - import guard
    import aussie_ecolens_db as db
except Exception:  # noqa: BLE001
    db = None

OCI_ML_ENDPOINT = os.getenv("OCI_ML_ENDPOINT")
OCI_API_TOKEN = os.getenv("OCI_API_TOKEN")
PRESIGN_EXPIRY = int(os.getenv("PRESIGN_EXPIRY", "600"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))

THUMBNAIL_LAMBDA_NAME = os.getenv("THUMBNAIL_LAMBDA_NAME")
THUMBNAIL_PREFIX = os.getenv("THUMBNAIL_PREFIX", "thumbnails/")
PERSIST_TO_DB = os.getenv("PERSIST_TO_DB", "true").lower() == "true"
DEFAULT_OWNER_ID = os.getenv("DEFAULT_OWNER_ID")
OWNER_METADATA_KEY = os.getenv("OWNER_METADATA_KEY", "owner-id")
NOTIFY_LAMBDA_NAME = os.getenv("NOTIFY_LAMBDA_NAME")

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


def _s3_client():
    import boto3

    return boto3.client("s3")


def _lambda_client():
    import boto3

    return boto3.client("lambda")


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


def _is_image(key: str) -> bool:
    lower = key.lower()
    return any(lower.endswith(ext) for ext in IMAGE_EXTENSIONS)


def _thumbnail_key_for(key: str) -> str:
    return f"{THUMBNAIL_PREFIX.rstrip('/')}/{Path(key).stem}.jpg"


def _owner_id_for(s3, bucket: str, key: str) -> str | None:
    """Resolve the uploader. owner_id is not present in the S3 event itself, so we
    read it from the object's user metadata (set by A at presigned-PUT time) and
    fall back to DEFAULT_OWNER_ID. D's write_record applies its own fallback too.
    """
    try:
        head = s3.head_object(Bucket=bucket, Key=key)
        metadata = head.get("Metadata", {}) or {}
        owner = metadata.get(OWNER_METADATA_KEY) or metadata.get(OWNER_METADATA_KEY.replace("-", "_"))
        if owner:
            return owner
    except Exception:  # noqa: BLE001 - metadata is best-effort
        pass
    return DEFAULT_OWNER_ID


def _async_invoke_thumbnail(lambda_client, bucket: str, key: str) -> dict[str, Any]:
    """Fire-and-forget invocation of the thumbnail Lambda (only one S3 target needed)."""
    if not THUMBNAIL_LAMBDA_NAME:
        return {"thumbnail_invoked": False, "reason": "THUMBNAIL_LAMBDA_NAME not configured"}
    try:
        lambda_client.invoke(
            FunctionName=THUMBNAIL_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps({"bucket": bucket, "key": key}).encode("utf-8"),
        )
        return {"thumbnail_invoked": True}
    except Exception as exc:  # noqa: BLE001
        return {"thumbnail_invoked": False, "error": f"{type(exc).__name__}: {exc}"}


def _call_oci(bucket: str, key: str, presigned_url: str, owner_id: str | None) -> dict[str, Any]:
    if not OCI_ML_ENDPOINT:
        raise RuntimeError("OCI_ML_ENDPOINT is not configured")

    payload = json.dumps(
        {
            "bucket": bucket,
            "key": key,
            "image_url": presigned_url,
            "original_url": f"https://{bucket}.s3.amazonaws.com/{key}",
            "owner_id": owner_id,
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if OCI_API_TOKEN:
        headers["Authorization"] = f"Bearer {OCI_API_TOKEN}"

    request = Request(OCI_ML_ENDPOINT, data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def _persist_record(oci_result: dict[str, Any], bucket: str, key: str, owner_id: str | None) -> dict[str, Any]:
    """Write the ML metadata to DynamoDB via D's shared write_record.

    Returns a small status dict merged into the per-object result.
    """
    if not PERSIST_TO_DB:
        return {"persisted": False, "reason": "PERSIST_TO_DB disabled"}
    if db is None:
        return {"persisted": False, "reason": "aussie_ecolens_db module not bundled"}
    if oci_result.get("status") != "ok":
        return {"persisted": False, "reason": "OCI result was not ok"}

    checksum = oci_result.get("checksum")
    try:
        # De-duplication guard: skip writing a second row for the same content.
        if checksum:
            existing = db.get_by_checksum(checksum)
            if existing:
                return {"persisted": False, "reason": "duplicate", "file_id": existing.get("file_id")}

        record = db.write_record(
            checksum=checksum or "",
            file_type=oci_result.get("file_type", "image"),
            original_url=oci_result.get("original_url") or f"https://{bucket}.s3.amazonaws.com/{key}",
            thumbnail_url=oci_result.get("thumbnail_url"),
            tags=oci_result.get("tags") or {},
            owner_id=owner_id,
            file_id=oci_result.get("file_id"),
            original_s3_key=key,
            thumbnail_s3_key=_thumbnail_key_for(key) if _is_image(key) else None,
        )
        return {"persisted": True, "file_id": record.get("file_id")}
    except Exception as exc:  # noqa: BLE001
        return {"persisted": False, "error": f"{type(exc).__name__}: {exc}"}


def _maybe_notify(lambda_client, record_info: dict[str, Any], oci_result: dict[str, Any]) -> None:
    """Trigger D's tag-based notification (no DynamoDB Stream exists, so do it here).

    Best-effort and gated on NOTIFY_LAMBDA_NAME. Only fires for newly persisted files
    that actually have tags.
    """
    if not NOTIFY_LAMBDA_NAME:
        return
    if not record_info.get("persisted"):
        return
    tags = oci_result.get("tags") or {}
    if not tags:
        return
    try:
        lambda_client.invoke(
            FunctionName=NOTIFY_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "action": "publish",
                    "file_id": record_info.get("file_id"),
                    "original_url": oci_result.get("original_url"),
                    "tags": tags,
                }
            ).encode("utf-8"),
        )
    except Exception:  # noqa: BLE001 - notification is best-effort
        pass


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    s3 = _s3_client()
    lambda_client = _lambda_client()
    results = []

    for record in _parse_records(event):
        bucket, key = record["bucket"], record["key"]
        if not _is_supported(key):
            results.append({"status": "skipped", "bucket": bucket, "key": key, "reason": "unsupported file type"})
            continue

        item: dict[str, Any] = {"bucket": bucket, "key": key}
        try:
            # 1) Async thumbnail (images only) so S3 needs only this single target.
            if _is_image(key):
                item.update(_async_invoke_thumbnail(lambda_client, bucket, key))

            # 2) Resolve owner, presign, and run inference on OCI.
            owner_id = _owner_id_for(s3, bucket, key)
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=PRESIGN_EXPIRY,
            )
            oci_result = _call_oci(bucket, key, presigned_url, owner_id)
            item["status"] = oci_result.get("status", "ok")
            item["tags"] = oci_result.get("tags")
            item["checksum"] = oci_result.get("checksum")

            # 3) Persist metadata (was previously lost on the async return path).
            persist_info = _persist_record(oci_result, bucket, key, owner_id)
            item.update(persist_info)

            # 4) Trigger tag-based notification if enabled.
            _maybe_notify(lambda_client, persist_info, oci_result)
        except Exception as exc:  # noqa: BLE001
            item["status"] = "error"
            item["error_type"] = type(exc).__name__
            item["message"] = str(exc)

        results.append(item)

    return {
        "status": "ok" if all(r.get("status") in ("ok", "skipped") for r in results) else "partial_error",
        "results": results,
    }
