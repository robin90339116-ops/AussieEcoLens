# Aussie EcoLens B Module Interface Contract

This document defines the interface for the Lambda + ML module owned by ZHU WENXUAN.
It is intended for integration with the authentication/API, frontend, database, and
notification modules.

## S3 Event Input

The thumbnail and ML tagging Lambdas both accept standard S3 `ObjectCreated` events.
For local testing, they also accept a simplified event:

```json
{
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/example.jpg",
  "checksum": "optional-sha256",
  "original_url": "https://example-bucket.s3.amazonaws.com/uploads/example.jpg"
}
```

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

The ML Lambda returns a metadata payload ready for database insertion by the D module.
The `tags` object uses common species names where available and stores counts, not only
single labels.

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
  presigned URLs, and Lambda execution roles.
- B module generates thumbnails, runs ML inference, packages the container image, and
  returns the metadata JSON shown above.
- C module uses `thumbnail_url`, `original_url`, and `tags` for UI preview and result display.
- D module persists the metadata record, supports query APIs, and triggers tag-based
  notifications after successful database insertion.
