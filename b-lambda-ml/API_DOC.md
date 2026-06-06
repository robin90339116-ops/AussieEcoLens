# Aussie EcoLens B Module API Documentation

Owner: ZHU WENXUAN  
Module: B - Lambda + ML  
Deployment route: AWS S3 trigger Lambda -> Oracle Cloud ML inference service

## Base URL

Current Oracle Cloud public IP:

```text
http://130.162.194.202:8080
```

Recommended production URL after TLS/reverse proxy:

```text
https://<oci-domain-or-load-balancer>
```

Important: the service must be running on the Oracle instance and port `8080` (or `443` if using HTTPS) must be open in both the OCI security list/NSG and the instance firewall.

## Authentication

All `/v1/*` endpoints require a bearer token:

```http
Authorization: Bearer <API_AUTH_TOKEN>
```

The same token must be configured in:

- OCI ML service: `API_AUTH_TOKEN`
- AWS trigger Lambda: `OCI_API_TOKEN`

Do not hardcode the token in frontend code. The frontend should call the team's authenticated API; the AWS backend/trigger Lambda should call this ML service.

## Health Check

Used to verify the service is alive and the models are loaded.

```http
GET /health
```

Example:

```bash
curl http://130.162.194.202:8080/health
```

Success response:

```json
{
  "status": "ok",
  "models_loaded": true,
  "load_error": null,
  "auth_required": true
}
```

## Endpoint 1: Tag S3 File

This is the main integration endpoint for A/D modules.

The AWS S3-triggered Lambda should generate a presigned GET URL for the uploaded file and call this endpoint. The OCI service downloads the file through that short-lived URL, runs MegaDetector + SpeciesNet, and returns metadata ready for database insertion.

```http
POST /v1/tag/s3
Content-Type: application/json
Authorization: Bearer <API_AUTH_TOKEN>
```

Full URL:

```text
http://130.162.194.202:8080/v1/tag/s3
```

Request body:

```json
{
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/Alectura_lathami_1.JPG",
  "image_url": "https://<short-lived-presigned-s3-url>",
  "original_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/uploads/Alectura_lathami_1.JPG",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg",
  "checksum": "optional-sha256"
}
```

Required fields:

- `bucket`: S3 bucket name.
- `key`: S3 object key.
- `image_url`: presigned URL or other temporary URL that the OCI service can download.

Optional fields:

- `original_url`: public/display URL for the full original file.
- `thumbnail_url`: URL of the image thumbnail, if already generated.
- `checksum`: SHA-256 checksum from the upload/deduplication module. If omitted, the
  service computes the SHA-256 of the downloaded bytes and returns it. This matches the
  frontend's `crypto.subtle.digest('SHA-256', ...)`, so de-duplication works end-to-end.
- `owner_id`: Cognito `sub` of the uploader, forwarded by the trigger Lambda.

Success response:

```json
{
  "status": "ok",
  "file_id": "4838f68beda023672f39c751958e5e51cdbb2c5b4c8c968c3769215f9d076354",
  "file_type": "image",
  "original_bucket": "aussie-ecolens-uploads",
  "original_key": "uploads/Alectura_lathami_1.JPG",
  "original_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/uploads/Alectura_lathami_1.JPG",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg",
  "checksum": "4838f68beda023672f39c751958e5e51cdbb2c5b4c8c968c3769215f9d076354",
  "tags": {
    "australian brushturkey": 1
  },
  "predictions": [
    {
      "scientific_name": "Alectura_lathami",
      "common_name": "australian brushturkey",
      "confidence": 0.9999760389328003,
      "source": "crop_0"
    }
  ],
  "created_at": "2026-06-01T15:39:18Z",
  "detections": 1
}
```

Notes for D module:

- Use `tags` for species query and minimum-count query.
- Use `thumbnail_url` for UI preview.
- Use `original_url` for full-size image/video access.
- Use `file_id` as a stable identifier.

## Endpoint 2: Tag Uploaded File

Used for the query-by-file feature. The file is uploaded directly to the ML service for temporary inference only and is not stored permanently.

```http
POST /v1/tag/upload
Content-Type: multipart/form-data
Authorization: Bearer <API_AUTH_TOKEN>
```

Full URL:

```text
http://130.162.194.202:8080/v1/tag/upload
```

Example:

```bash
curl -X POST "http://130.162.194.202:8080/v1/tag/upload" \
  -H "Authorization: Bearer <API_AUTH_TOKEN>" \
  -F "file=@Alectura_lathami_1.JPG"
```

Success response:

```json
{
  "status": "ok",
  "file_type": "image",
  "checksum": "4838f68beda023672f39c751958e5e51cdbb2c5b4c8c968c3769215f9d076354",
  "tags": {
    "australian brushturkey": 1
  },
  "predictions": [
    {
      "scientific_name": "Alectura_lathami",
      "confidence": 0.9999760389328003,
      "source": "Alectura_lathami_1-0",
      "common_name": "australian brushturkey"
    }
  ]
}
```

D's Q4 (query-by-file) should call this endpoint with `multipart/form-data` and use the
returned `checksum` to look up existing records via `get_by_checksum`.

## Endpoint 3: Generate Thumbnail From S3 URL

This endpoint generates thumbnail metadata from a presigned image URL. In the current design, actual thumbnail upload to S3 can be handled by the AWS thumbnail Lambda or caller.

```http
POST /v1/thumbnail/s3
Content-Type: application/json
Authorization: Bearer <API_AUTH_TOKEN>
```

Full URL:

```text
http://130.162.194.202:8080/v1/thumbnail/s3
```

Request body:

```json
{
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/Alectura_lathami_1.JPG",
  "image_url": "https://<short-lived-presigned-s3-url>",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg"
}
```

Success response:

```json
{
  "status": "ok",
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/Alectura_lathami_1.JPG",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg",
  "width": 320,
  "height": 240,
  "content_type": "image/jpeg",
  "note": "Thumbnail bytes generated. Upload to storage is handled by the caller/trigger on OCI or AWS."
}
```

## Error Responses

Missing token:

```json
{
  "detail": "Missing bearer token"
}
```

Invalid token:

```json
{
  "detail": "Invalid token"
}
```

Unsupported file:

```json
{
  "status": "error",
  "error_type": "UnsupportedFileType",
  "message": "Only image and video files are supported",
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/example.txt",
  "created_at": "2026-06-01T15:39:18Z"
}
```

## Supported File Types

Images:

```text
.jpg, .jpeg, .png, .webp
```

Videos:

```text
.mp4, .mov, .avi, .mkv
```

For videos, the service extracts frames at 1 frame per second before classification.

## AWS Trigger Lambda Configuration

The A module / AWS side should configure `s3_trigger_lambda.py` (the single S3
notification target on `uploads/`) with:

```text
OCI_ML_ENDPOINT=http://130.162.194.202:8080/v1/tag/s3
OCI_API_TOKEN=<same value as API_AUTH_TOKEN on OCI service>
PRESIGN_EXPIRY=600
REQUEST_TIMEOUT=300

THUMBNAIL_LAMBDA_NAME=aussie-ecolens-thumbnail   # async fan-out (S3 single-target rule)
PERSIST_TO_DB=true                               # write results via D's write_record
DEFAULT_OWNER_ID=demo-owner                      # fallback owner_id
OWNER_METADATA_KEY=owner-id                      # S3 user-metadata key set by A
FILES_TABLE=AussieEcoLensFiles
AWS_REGION=us-east-1
NOTIFY_LAMBDA_NAME=aussie-ecolens-notifications  # optional tag-based notification
```

The forwarding Lambda now: (1) async-invokes the thumbnail Lambda, (2) calls this ML
service, (3) writes the metadata to DynamoDB `AussieEcoLensFiles` using D's shared
`aussie_ecolens_db.write_record` (the zip must bundle D's `aussie_ecolens_db.py`), and
(4) optionally publishes a tag-based notification. This fixes the previous issue where
the async S3 trigger's result was discarded and the database stayed empty.

Recommended production setting after HTTPS is configured:

```text
OCI_ML_ENDPOINT=https://<oci-domain-or-load-balancer>/v1/tag/s3
```

## Important Current Status

The service is currently running on the Oracle Cloud instance as a systemd service:

```text
service: aussie-ecolens-ml.service
status: enabled + active
public health URL: http://130.162.194.202:8080/health
main inference URL: http://130.162.194.202:8080/v1/tag/s3
```

Verified public checks:

- `GET /health` returns HTTP 200 with `models_loaded: true`.
- `POST /v1/tag/upload` returns HTTP 200 and successfully identifies `Sus_scrofa_1.JPG` as `wild boar`.

The API token is stored on the OCI instance in:

```text
/home/ubuntu/fit5225/ass2/AussieEcoLense/.env
```

Do not expose this token in frontend code. Share it only with the backend/AWS trigger Lambda owner.
