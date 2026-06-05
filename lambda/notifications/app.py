from __future__ import annotations

import sys
from pathlib import Path

SHARED_DIR = Path(__file__).resolve().parents[1] / "shared"
sys.path.insert(0, str(SHARED_DIR))

from http_utils import parse_json_body, response
from sns_helpers import publish_new_file_notification, subscribe_email, unsubscribe_email


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method") or event.get("httpMethod")
    if method == "OPTIONS":
        return response(204, {})

    body = parse_json_body(event)
    action = str(body.get("action", "")).lower()

    if action == "subscribe":
        user_email = body.get("user_email")
        species_list = body.get("species_list") or body.get("species")
        if not user_email or not isinstance(species_list, list) or not species_list:
            return response(400, {"error": "user_email and non-empty species_list are required"})
        return response(200, subscribe_email(user_email=user_email, species_list=species_list))

    if action == "unsubscribe":
        user_email = body.get("user_email")
        if not user_email:
            return response(400, {"error": "user_email is required"})
        return response(
            200,
            unsubscribe_email(
                user_email=user_email,
                subscription_arn=body.get("subscription_arn"),
                species_list=body.get("species_list"),
            ),
        )

    if action == "publish":
        required = ["file_id", "original_url", "tags"]
        missing = [key for key in required if key not in body]
        if missing:
            return response(400, {"error": f"missing fields: {', '.join(missing)}"})
        return response(
            200,
            publish_new_file_notification(
                file_id=body["file_id"],
                original_url=body["original_url"],
                tags=body["tags"],
            ),
        )

    return response(400, {"error": "action must be subscribe, unsubscribe, or publish"})
