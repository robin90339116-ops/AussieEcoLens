from __future__ import annotations

import base64
import importlib.util
import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def api_event(body: dict | None = None, method: str = "POST", query: dict | None = None):
    return {
        "requestContext": {"http": {"method": method}},
        "queryStringParameters": query or {},
        "body": json.dumps(body or {}),
    }


def body_of(response: dict):
    return json.loads(response["body"])


def multipart_event(file_bytes: bytes, fields: dict[str, str] | None = None):
    boundary = "----testboundary"
    parts: list[bytes] = []
    for name, value in (fields or {}).items():
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    parts.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            b'Content-Disposition: form-data; name="file"; filename="query.jpg"\r\n',
            b"Content-Type: image/jpeg\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )
    return {
        "requestContext": {"http": {"method": "POST"}},
        "headers": {"content-type": f"multipart/form-data; boundary={boundary}"},
        "body": b"".join(parts),
    }


class HandlerTests(unittest.TestCase):
    def test_http_utils_parses_base64_json_body(self):
        http_utils = load_module("test_http_utils", "lambda/shared/http_utils.py")
        encoded = base64.b64encode(b'{"species":"wombat"}').decode("ascii")
        parsed = http_utils.parse_json_body({"body": encoded, "isBase64Encoded": True})
        self.assertEqual(parsed, {"species": "wombat"})

    def test_q3_thumbnail_lookup_success(self):
        q3 = load_module("test_q3_app", "lambda/queries-aws/q3_thumbnail_lookup/app.py")
        q3.get_by_thumbnail_url = lambda url: {
            "file_id": "file-1",
            "thumbnail_url": url,
            "original_url": "https://example.com/original.jpg",
            "tags": {"wombat": 2},
            "type": "image",
        }

        response = q3.lambda_handler(api_event({"thumbnail_url": "thumb-url"}), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body_of(response)["original_url"], "https://example.com/original.jpg")

    def test_q3_thumbnail_lookup_requires_url(self):
        q3 = load_module("test_q3_app_missing", "lambda/queries-aws/q3_thumbnail_lookup/app.py")
        response = q3.lambda_handler(api_event({}), None)
        self.assertEqual(response["statusCode"], 400)

    def test_q4_query_image_does_not_store_query_image(self):
        q4 = load_module("test_q4_app", "lambda/queries-aws/q4_image_search/app.py")
        q4._invoke_oracle_tag_upload = lambda file_data: {"tags": {"wombat": 2, "magpie": 1}}
        q4.query_by_tag_counts = lambda tags, owner_id=None, limit=100: [
            {"file_id": "file-1", "tags": tags}
        ]

        response = q4.lambda_handler(api_event({"image_base64": "YWJj", "limit": 10}), None)
        payload = body_of(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertFalse(payload["query_image_stored"])
        self.assertEqual(payload["query_type"], "Q4_IMAGE_TO_TAGS_THEN_Q1")
        self.assertEqual(payload["count"], 1)

    def test_q4_rejects_missing_image(self):
        q4 = load_module("test_q4_app_missing", "lambda/queries-aws/q4_image_search/app.py")
        response = q4.lambda_handler(api_event({}), None)
        self.assertEqual(response["statusCode"], 400)

    def test_q4_accepts_multipart_file(self):
        q4 = load_module("test_q4_app_multipart", "lambda/queries-aws/q4_image_search/app.py")
        q4._invoke_oracle_tag_upload = lambda file_data: {"species": ["koala"]}
        q4.query_by_tag_counts = lambda tags, owner_id=None, limit=100: [
            {"file_id": "file-1", "tags": tags, "owner_id": owner_id}
        ]

        response = q4.lambda_handler(multipart_event(b"\xff\xd8image", {"limit": "5", "owner_id": "user-1"}), None)
        payload = body_of(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(payload["tags"], {"koala": 1})

    def test_q5_update_tags_partial_success(self):
        q5 = load_module("test_q5_app", "lambda/queries-aws/q5_update_tags/app.py")
        q5.update_tags = lambda urls, tags, operation: {
            "updated": [{"file_id": "file-1"}],
            "errors": [{"url": "missing", "error": "not_found"}],
        }

        response = q5.lambda_handler(
            api_event({"urls": ["ok", "missing"], "tags": {"koala": 1}, "operation": "add"}),
            None,
        )
        self.assertEqual(response["statusCode"], 207)
        self.assertEqual(len(body_of(response)["errors"]), 1)

    def test_q5_rejects_bad_operation(self):
        q5 = load_module("test_q5_app_bad_op", "lambda/queries-aws/q5_update_tags/app.py")

        def bad_update_tags(urls, tags, operation):
            raise ValueError("operation must be add/1 or remove/0")

        q5.update_tags = bad_update_tags
        response = q5.lambda_handler(
            api_event({"urls": ["url"], "tags": {"koala": 1}, "operation": "bad"}),
            None,
        )
        self.assertEqual(response["statusCode"], 400)

    def test_q6_delete_file_calls_media_and_db_delete(self):
        q6 = load_module("test_q6_app", "lambda/queries-aws/q6_delete_file/app.py")
        item = {"file_id": "file-1", "original_url": "https://bucket.s3.us-east-1.amazonaws.com/a.jpg"}
        q6.get_by_file_id = lambda file_id: item
        q6._delete_media_objects = lambda record: [{"bucket": "bucket", "key": "a.jpg"}]
        q6.delete_record = lambda file_id=None, url=None: {"file_id": file_id}

        response = q6.lambda_handler(api_event({"file_id": "file-1"}, method="DELETE"), None)
        payload = body_of(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(payload["deleted"][0]["deleted_file_id"], "file-1")
        self.assertEqual(payload["deleted"][0]["deleted_s3_objects"][0]["key"], "a.jpg")

    def test_notifications_subscribe_validation(self):
        notifications = load_module("test_notifications_app", "lambda/notifications/app.py")
        response = notifications.lambda_handler(api_event({"action": "subscribe"}), None)
        self.assertEqual(response["statusCode"], 400)

    def test_notifications_subscribe_success(self):
        notifications = load_module("test_notifications_app_success", "lambda/notifications/app.py")
        notifications.subscribe_email = lambda user_email, species_list: {
            "subscription_arn": "pending",
            "subscription": {"user_email": user_email, "species_list": species_list},
            "confirmation_required": True,
        }
        response = notifications.lambda_handler(
            api_event(
                {
                    "action": "subscribe",
                    "user_email": "student@example.com",
                    "species_list": ["wombat"],
                }
            ),
            None,
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertTrue(body_of(response)["confirmation_required"])

    def test_notifications_list_get(self):
        notifications = load_module("test_notifications_app_list", "lambda/notifications/app.py")
        notifications.list_subscriptions = lambda user_email=None: [
            {"user_email": user_email or "student@example.com", "species_list": ["wombat"]}
        ]
        response = notifications.lambda_handler(
            {
                "requestContext": {"http": {"method": "GET"}},
                "queryStringParameters": {"email": "student@example.com"},
            },
            None,
        )
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body_of(response)["subscriptions"][0]["species_list"], ["wombat"])


if __name__ == "__main__":
    unittest.main()
