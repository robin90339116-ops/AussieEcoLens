# Aussie EcoLens B Module Interface Contract

This document defines the interface for the Lambda + ML module owned by ZHU WENXUAN.
It is intended for integration with the authentication/API, frontend, database, and
notification modules.

## Upload pipeline (Route B)

The S3 `uploads/` event has a **single** notification target: the forwarding Lambda
(`s3_trigger_lambda.py`). It fans out the work itself:

1. async-invokes the thumbnail Lambda (`InvocationType="Event"`),
2. calls the OCI ML service (`/v1/tag/s3`) with a presigned URL + bearer token,
3. persists the returned metadata to DynamoDB via D's `aussie_ecolens_db.write_record`,
4. optionally publishes a tag-based notification through D's notifications Lambda.

## S3 Event Input

The thumbnail and ML Lambdas accept standard S3 `ObjectCreated` events. For local
testing, they also accept a simplified event:

```json
{
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/example.jpg",
  "checksum": "optional-sha256",
  "original_url": "https://example-bucket.s3.amazonaws.com/uploads/example.jpg"
}
```

`owner_id` is not present in the S3 event. By convention A sets it as S3 user metadata
`x-amz-meta-owner-id` (Cognito `sub`) on the presigned PUT; the forwarding Lambda reads it
via `head_object` and falls back to `DEFAULT_OWNER_ID`.

## Thumbnail Lambda Output

```json
{
  "status": "ok",
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/example.jpg",
  "thumbnail_bucket": "aussie-ecolens-uploads",
  "thumbnail_key": "thumbnails/example.jpg",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/example.jpg",
  "width": 320,
  "height": 214,
  "content_type": "image/jpeg"
}
```

## ML Tagging Lambda Output

The OCI ML service (and the legacy ML Lambda) returns a metadata payload that the
forwarding Lambda persists via D's `write_record`. The `checksum` field is the SHA-256
of the stored bytes (matches the frontend's SHA-256 for de-duplication). The `tags`
object uses common species names where available and stores counts, not only single
labels.

```json
{
  "status": "ok",
  "file_id": "sha256-or-stable-key-hash",
  "file_type": "image",
  "original_bucket": "aussie-ecolens-uploads",
  "original_key": "uploads/example.jpg",
  "original_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/uploads/example.jpg",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/example.jpg",
  "checksum": "optional-sha256",
  "tags": {
    "dingo": 1
  },
  "predictions": [
    {
      "scientific_name": "Canis_dingo",
      "common_name": "dingo",
      "confidence": 0.91,
      "source": "crop_0"
    }
  ],
  "created_at": "2026-06-01T14:30:00Z"
}
```

## Error Output

Handlers should return structured errors instead of crashing during the demo.

```json
{
  "status": "error",
  "error_type": "UnsupportedFileType",
  "message": "Only image and video files are supported",
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/example.txt"
}
```

## Ownership Boundaries

- A module provides the upload bucket, object key pattern, authentication, API Gateway,
  presigned URLs (setting `x-amz-meta-owner-id`), Lambda execution roles, and configures the
  bucket so the single `uploads/` notification points at B's forwarding Lambda.
- B module runs the forwarding Lambda (fan-out + presign + bearer auth), generates
  thumbnails, runs ML inference on OCI, computes the SHA-256 checksum, and **persists the
  metadata to DynamoDB via D's `aussie_ecolens_db.write_record`** after a successful call.
- C module uses `thumbnail_url`, `original_url`, and `tags` for UI preview and result display.
- D module owns the DynamoDB schema + shared `aussie_ecolens_db` module, the query APIs, and
  the notifications Lambda. Because the table has no DynamoDB Stream, B explicitly invokes D's
  notification `publish` (when `NOTIFY_LAMBDA_NAME` is set) after persisting a tagged file.
