# AussieEcoLens D group API contract

This document is the handoff contract for D group's database, query, GCP, and notification work.

## Scope

D group owns:

- DynamoDB schema and shared helper library.
- AWS Lambda APIs: Q3, Q4, Q5, Q6, notification subscribe/unsubscribe/publish.
- GCP Cloud Functions: Q1 and Q2.
- Cognito JWT verification on GCP.
- SNS notification helper.

Reports and final slides are intentionally not included yet.

## Integration boundary for demo

For the formal frontend demo, use A's API Gateway as the main public backend entry point:

- Frontend should call A's API Gateway whenever possible.
- D's AWS Lambda handlers for Q3/Q4/Q5/Q6 and notifications must be attached behind A's API Gateway with Cognito Authorizer.
- B's ML Lambda must stay behind backend services. The frontend must not call B directly.
- D's GCP Q1/Q2 endpoints may be exposed directly only if they are public HTTPS endpoints with Cognito JWT verification enabled.

This repo already includes the GCP JWT verification middleware for Q1/Q2. Keep `AUTH_REQUIRED=true` outside local smoke tests.

## Environment

Common AWS environment variables:

- `AWS_REGION=ap-southeast-2`
- `FILES_TABLE=AussieEcoLensFiles`
- `NOTIFICATIONS_TABLE=AussieEcoLensNotificationsSub`
- `CHECKSUM_INDEX=checksum-index`
- `SNS_TOPIC_ARN=arn:aws:sns:...`
- `CORS_ALLOW_ORIGIN=http://localhost:5173`

GCP Function environment variables:

- `AWS_REGION=ap-southeast-2`
- `FILES_TABLE=AussieEcoLensFiles`
- `COGNITO_REGION=ap-southeast-2`
- `COGNITO_USER_POOL_ID=<from A>`
- `COGNITO_APP_CLIENT_ID=<from A>`
- `AUTH_REQUIRED=true`
- `CORS_ALLOW_ORIGIN=<frontend origin>`

For local smoke tests only, `AUTH_REQUIRED=false` can be used.

## DynamoDB schema

### `AussieEcoLensFiles`

Primary key:

- `file_id` string

Attributes:

- `checksum`: SHA-256 checksum.
- `type`: `image` or `video`.
- `original_url`: original media URL.
- `thumbnail_url`: thumbnail URL.
- `tags`: species count map, for example `{ "wombat": 2, "magpie": 1 }`.
- `owner_id`: Cognito user `sub` or email.
- `upload_time`: UTC ISO timestamp.
- `last_modified`: UTC ISO timestamp.
- `original_s3_key`: optional, used by Q6 deletion.
- `thumbnail_s3_key`: optional, used by Q6 deletion.

Indexes:

- `checksum-index`: partition key `checksum`, for A's dedup Lambda.
- `owner_id-index`: partition key `owner_id`, for user-specific listing.

### `AussieEcoLensNotificationsSub`

Primary key:

- `user_email` string

Attributes:

- `species_list`: subscribed species names.
- `created_at`: UTC ISO timestamp.

## Shared helper for A and B

Location: `Project/lambda/shared/aussie_ecolens_db.py`

A should use:

```python
from aussie_ecolens_db import get_by_checksum

existing = get_by_checksum(checksum)
```

B should use:

```python
from aussie_ecolens_db import write_record
from sns_helpers import publish_new_file_notification

record = write_record(
    checksum=checksum,
    file_type="image",
    original_url=original_url,
    thumbnail_url=thumbnail_url,
    tags={"wombat": 2},
    owner_id=owner_id,
    original_s3_key=original_s3_key,
    thumbnail_s3_key=thumbnail_s3_key,
)

publish_new_file_notification(
    file_id=record["file_id"],
    original_url=record["original_url"],
    tags=record["tags"],
)
```

## Auth format

Frontend should call protected endpoints with:

```http
Authorization: Bearer <cognito_jwt>
```

AWS-side D endpoints should normally receive this through A's API Gateway + Cognito Authorizer. GCP Q1/Q2 verifies Cognito JWKS, RS256 signature, issuer, audience, and expiry when exposed directly.

## Q1: tag + count AND query

Owner: D. Platform: GCP Cloud Functions.

Endpoint:

```http
POST <A_API_GATEWAY_Q1_URL or GCP_Q1_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Preferred demo route: A API Gateway. Direct GCP route is acceptable only when `AUTH_REQUIRED=true` and Cognito JWT settings are configured.

Request:

```json
{
  "tags": {
    "wombat": 2,
    "magpie": 1
  },
  "limit": 50
}
```

Response:

```json
{
  "query_type": "Q1_AND_TAG_COUNTS",
  "logic": "AND",
  "count": 1,
  "items": [
    {
      "file_id": "file-001",
      "original_url": "https://...",
      "thumbnail_url": "https://...",
      "tags": {
        "wombat": 2,
        "magpie": 1
      }
    }
  ]
}
```

Curl:

```bash
curl -X POST "$GCP_Q1_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags":{"wombat":2,"magpie":1},"limit":50}'
```

Important: Q1 is AND logic. A file must satisfy every requested species/count pair.

## Q2: species exists query

Owner: D. Platform: GCP Cloud Functions.

Endpoint:

```http
POST <A_API_GATEWAY_Q2_URL or GCP_Q2_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Preferred demo route: A API Gateway. Direct GCP route is acceptable only when `AUTH_REQUIRED=true` and Cognito JWT settings are configured.

Request:

```json
{
  "species": "wombat",
  "limit": 50
}
```

Response:

```json
{
  "query_type": "Q2_SPECIES_EXISTS",
  "species": "wombat",
  "count": 2,
  "items": []
}
```

Curl:

```bash
curl -X POST "$GCP_Q2_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"species":"wombat","limit":50}'
```

## Q3: thumbnail URL to original URL

Owner: D. Platform: AWS Lambda + API Gateway.

Endpoint:

```http
POST <AWS_Q3_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "thumbnail_url": "https://bucket.s3.ap-southeast-2.amazonaws.com/thumbs/file-001.jpg"
}
```

Response:

```json
{
  "file_id": "file-001",
  "thumbnail_url": "https://...",
  "original_url": "https://...",
  "tags": {
    "wombat": 2
  },
  "type": "image"
}
```

Curl:

```bash
curl -X POST "$AWS_Q3_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"thumbnail_url":"https://bucket.s3.ap-southeast-2.amazonaws.com/thumbs/file-001.jpg"}'
```

## Q4: query by uploaded image

Owner: D + B. Platform: AWS Lambda + B's ML Lambda.

Endpoint:

```http
POST <AWS_Q4_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "image_base64": "<base64 image bytes>",
  "content_type": "image/jpeg",
  "limit": 50
}
```

Alternative request:

```json
{
  "image_url": "https://temporary-query-image-url",
  "limit": 50
}
```

Response:

```json
{
  "query_type": "Q4_IMAGE_TO_TAGS_THEN_Q1",
  "query_image_stored": false,
  "tags": {
    "wombat": 1
  },
  "count": 3,
  "items": []
}
```

Constraint: the query image is not written to S3 or DynamoDB.

## Q5: batch add/remove tags

Owner: D. Platform: AWS Lambda + API Gateway.

Endpoint:

```http
POST <AWS_Q5_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Add request:

```json
{
  "urls": ["https://bucket.s3.ap-southeast-2.amazonaws.com/originals/file-001.jpg"],
  "tags": {
    "wombat": 2
  },
  "operation": "add"
}
```

Remove request:

```json
{
  "urls": ["https://bucket.s3.ap-southeast-2.amazonaws.com/originals/file-001.jpg"],
  "tags": ["wombat"],
  "operation": "remove"
}
```

Response:

```json
{
  "updated": [],
  "errors": []
}
```

Curl:

```bash
curl -X POST "$AWS_Q5_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://bucket.s3.ap-southeast-2.amazonaws.com/originals/file-001.jpg"],"tags":{"wombat":2},"operation":"add"}'
```

## Q6: delete file

Owner: D. Platform: AWS Lambda + API Gateway.

Endpoint:

```http
DELETE <AWS_Q6_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Request:

```json
{
  "file_id": "file-001"
}
```

Alternative request:

```json
{
  "url": "https://bucket.s3.ap-southeast-2.amazonaws.com/originals/file-001.jpg"
}
```

Response:

```json
{
  "deleted_file_id": "file-001",
  "deleted_s3_objects": [
    {
      "bucket": "bucket",
      "key": "originals/file-001.jpg"
    }
  ],
  "deleted_record": {}
}
```

Curl:

```bash
curl -X DELETE "$AWS_Q6_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"file_id":"file-001"}'
```

## Notification API

Owner: D. Platform: AWS Lambda + API Gateway + SNS.

Endpoint:

```http
POST <AWS_NOTIFICATION_URL>
Authorization: Bearer <token>
Content-Type: application/json
```

Subscribe:

```json
{
  "action": "subscribe",
  "user_email": "student@example.com",
  "species_list": ["wombat", "magpie"]
}
```

Unsubscribe:

```json
{
  "action": "unsubscribe",
  "user_email": "student@example.com",
  "species_list": ["wombat"]
}
```

Publish helper for B:

```json
{
  "action": "publish",
  "file_id": "file-001",
  "original_url": "https://...",
  "tags": {
    "wombat": 2
  }
}
```

Curl:

```bash
curl -X POST "$AWS_NOTIFICATION_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"subscribe","user_email":"student@example.com","species_list":["wombat"]}'
```

## Deployment order

1. Deploy DynamoDB tables from `Project/infra/dynamodb/template.yaml`.
2. Deploy SNS topic from `Project/infra/sns/template.yaml`.
3. Package `Project/lambda/shared` as a layer or copy it into Lambda packages.
4. Deploy AWS Lambdas under `Project/lambda/queries-aws`.
5. Ask A to connect API Gateway + Cognito Authorizer to Q3/Q4/Q5/Q6 and notification endpoints.
6. Keep B's ML Lambda private behind backend services. Q4 invokes it by `ML_QUERY_LAMBDA_NAME`.
7. Deploy GCP Q1/Q2 functions from `Project/gcp-functions/queries-gcp` with `AUTH_REQUIRED=true`.
8. Prefer routing Q1/Q2 through A's API Gateway. If not, give C the protected GCP HTTPS URLs and confirm Cognito JWT settings are configured.
9. Give C the final endpoint URLs and this API contract.

API Gateway route handoff for A is in `Project/infra/api-gateway/d-group-openapi-fragment.yaml`.
Environment variable placeholders are listed in `Project/.env.example`.

## Current status

Implemented now:

- D1 schema and helper library.
- D2 Q3/Q5/Q6 Lambda handlers.
- D3 Q1/Q2 GCP handlers, CORS, and JWT verification.
- D4 Q4 Lambda handler skeleton integrated with B's ML Lambda contract.
- D5 SNS helper and notification Lambda.
- D6.1 API documentation.
- A API Gateway route handoff fragment.
- Demo checklist and architecture diagram draft.
- Local smoke test and handler unit tests.

Not done by request:

- D6.2 final architecture diagram with official AWS/GCP icons.
- D6.3/D6.4 team report.
- D6.5 individual report.
- Final cloud deployment, because real AWS/GCP credentials and A's Cognito values are needed.
