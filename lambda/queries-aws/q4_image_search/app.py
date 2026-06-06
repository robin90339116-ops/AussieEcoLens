from __future__ import annotations

import base64
import json
import os
import sys
import uuid
from email.parser import BytesParser
from email.policy import default
from pathlib import Path
from typing import Any
from urllib import request as urlrequest

import boto3

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from aussie_ecolens_db import query_by_tag_counts
from http_utils import parse_json_body, response


def _headers(event: dict[str, Any]) -> dict[str, str]:
    return {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}


def _raw_body(event: dict[str, Any]) -> bytes:
    raw = event.get("body") or b""
    if isinstance(raw, bytes):
        return raw
    if event.get("isBase64Encoded"):
        return base64.b64decode(raw)
    return str(raw).encode("utf-8")


def _extract_multipart_file(event: dict[str, Any]) -> dict[str, Any] | None:
    content_type = _headers(event).get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        return None

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + _raw_body(event)
    )
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if name not in {"file", "image", "upload"}:
            continue
        data = part.get_payload(decode=True)
        if not data:
            continue
        return {
            "bytes": data,
            "filename": part.get_filename() or f"query-{uuid.uuid4().hex}.jpg",
            "content_type": part.get_content_type() or "application/octet-stream",
        }
    return None


def _extract_multipart_fields(event: dict[str, Any]) -> dict[str, Any]:
    content_type = _headers(event).get("content-type", "")
    if not content_type.startswith("multipart/form-data"):
        return {}

    message = BytesParser(policy=default).parsebytes(
        f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + _raw_body(event)
    )
    fields: dict[str, Any] = {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name or name in {"file", "image", "upload"}:
            continue
        data = part.get_payload(decode=True)
        if data is not None:
            fields[name] = data.decode("utf-8")
    return fields


def _extract_json_file(body: dict[str, Any]) -> dict[str, Any] | None:
    image_base64 = body.get("image_base64")
    if not image_base64:
        return None
    return {
        "bytes": base64.b64decode(image_base64),
        "filename": body.get("filename") or "query.jpg",
        "content_type": body.get("content_type", "image/jpeg"),
    }


def _normalise_ml_tags(result: dict[str, Any]) -> dict[str, Any]:
    tags = result.get("tags")
    if isinstance(tags, dict) and tags:
        return tags

    species = result.get("species")
    if isinstance(species, list) and species:
        return {str(item): 1 for item in species}

    predictions = result.get("predictions") or result.get("labels")
    if isinstance(predictions, list):
        normalised: dict[str, int] = {}
        for item in predictions:
            if isinstance(item, str):
                normalised[item] = max(normalised.get(item, 0), 1)
            elif isinstance(item, dict):
                label = item.get("label") or item.get("species") or item.get("name")
                if label:
                    normalised[str(label)] = int(item.get("count", 1))
        if normalised:
            return normalised

    return {}


def _invoke_oracle_tag_upload(file_data: dict[str, Any]) -> dict[str, Any]:
    upload_url = os.getenv("ORACLE_TAG_UPLOAD_URL")
    token = os.getenv("ORACLE_API_TOKEN")
    if not upload_url:
        raise RuntimeError("ORACLE_TAG_UPLOAD_URL is not configured")
    if not token:
        raise RuntimeError("ORACLE_API_TOKEN is not configured")

    boundary = f"----AussieEcoLens{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            f'Content-Disposition: form-data; name="file"; filename="{file_data["filename"]}"\r\n'.encode("utf-8"),
            f"Content-Type: {file_data['content_type']}\r\n\r\n".encode("utf-8"),
            file_data["bytes"],
            f"\r\n--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    req = urlrequest.Request(
        upload_url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    with urlrequest.urlopen(req, timeout=int(os.getenv("ORACLE_TIMEOUT_SECONDS", "30"))) as result:
        return json.loads(result.read().decode("utf-8"))


def _invoke_ml_query_lambda(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = os.getenv("ML_QUERY_LAMBDA_NAME")
    if not function_name:
        raise RuntimeError("ML_QUERY_LAMBDA_NAME is not configured")

    client = boto3.client("lambda", region_name=os.getenv("AWS_REGION", "us-east-1"))
    result = client.invoke(
        FunctionName=function_name,
        InvocationType="RequestResponse",
        Payload=json.dumps(payload).encode("utf-8"),
    )
    raw_payload = result["Payload"].read().decode("utf-8")
    decoded = json.loads(raw_payload) if raw_payload else {}
    if "body" in decoded and isinstance(decoded["body"], str):
        return json.loads(decoded["body"])
    return decoded


def _infer_tags(event: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
    file_data = _extract_multipart_file(event) or _extract_json_file(body)
    if file_data:
        return _normalise_ml_tags(_invoke_oracle_tag_upload(file_data))

    image_url = body.get("image_url")
    if image_url:
        return _normalise_ml_tags(
            _invoke_ml_query_lambda(
                {
                    "mode": "query_image",
                    "image_url": image_url,
                    "content_type": body.get("content_type", "image/jpeg"),
                }
            )
        )
    return {}


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    if _headers(event).get("content-type", "").startswith("multipart/form-data"):
        body = {}
    else:
        try:
            body = parse_json_body(event)
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {}
    body = {**_extract_multipart_fields(event), **body}

    if not (_extract_multipart_file(event) or body.get("image_base64") or body.get("image_url")):
        return response(400, {"error": "multipart file, image_base64, or image_url is required"})

    try:
        tags = _infer_tags(event, body)
    except RuntimeError as exc:
        return response(500, {"error": "tag_service_not_configured", "detail": str(exc)})

    if not tags:
        return response(422, {"error": "tag_service_returned_no_tags"})

    limit = int(body.get("limit", 100))
    owner_id = body.get("owner_id")
    matches = query_by_tag_counts(tags, owner_id=owner_id, limit=limit)

    return response(
        200,
        {
            "query_type": "Q4_IMAGE_TO_TAGS_THEN_Q1",
            "query_image_stored": False,
            "tags": tags,
            "count": len(matches),
            "items": matches,
        },
    )
