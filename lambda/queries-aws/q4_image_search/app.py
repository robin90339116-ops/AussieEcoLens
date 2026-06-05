from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import boto3

SHARED_DIR = Path(__file__).resolve().parents[2] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from aussie_ecolens_db import query_by_tag_counts
from http_utils import parse_json_body, response


def _invoke_ml_query_lambda(payload: dict[str, Any]) -> dict[str, Any]:
    function_name = os.getenv("ML_QUERY_LAMBDA_NAME")
    if not function_name:
        raise RuntimeError("ML_QUERY_LAMBDA_NAME is not configured")

    client = boto3.client("lambda", region_name=os.getenv("AWS_REGION", "ap-southeast-2"))
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


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    body = parse_json_body(event)
    image_base64 = body.get("image_base64")
    image_url = body.get("image_url")
    content_type = body.get("content_type", "image/jpeg")

    if not image_base64 and not image_url:
        return response(400, {"error": "image_base64 or image_url is required"})

    # Query images are passed to B's ML Lambda only for inference. This function
    # deliberately does not write the query image to S3 or DynamoDB.
    ml_result = _invoke_ml_query_lambda(
        {
            "mode": "query_image",
            "image_base64": image_base64,
            "image_url": image_url,
            "content_type": content_type,
        }
    )
    tags = ml_result.get("tags")
    if not isinstance(tags, dict) or not tags:
        return response(422, {"error": "ml_lambda_returned_no_tags", "ml_result": ml_result})

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

