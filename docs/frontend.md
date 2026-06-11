# Frontend Implementation

## Scope

The React frontend covers the Assignment 2 UI criteria for authentication, upload, query, result preview, tag management, deletion, and tag-based notifications.

## Routes

| Route | Purpose | Main APIs |
| --- | --- | --- |
| `/login` | Cognito sign-in and challenge handoff | Cognito Auth |
| `/signup` | Cognito registration with email, first name, last name, password | Cognito Auth |
| `/verify` | Email verification code confirmation | Cognito Auth |
| `/new-password` | Temporary-password replacement | Cognito Auth |
| `/upload` | Media selection, presigned URL upload, progress, optional processing status | `POST /upload/presigned`, S3 `PUT`, optional status path |
| `/search` | Q1 tag-count AND query, Q2 species query, Q3 thumbnail URL lookup, Q4 uploaded-file query | `/query/by-tags`, `/query/by-species`, `/query/by-thumbnail`, `/query/by-file` |
| `/results` | Thumbnail/video gallery and Q3 full-size lookup | `/query/by-thumbnail` |
| `/tag-manage` | Q5 bulk add/remove tags | `/tags/modify` |
| `/delete` | Q6 multi-select deletion with confirmation | `DELETE /files` |
| `/subscribe` | Tag subscription and cancellation | `/notifications/subscribe` |

## Configuration

Copy `frontend/.env.example` to `frontend/.env` and fill in the values supplied by the team:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `VITE_USE_MOCKS=false` when real AWS/GCP/ML endpoints are available.
For local cloud integration, open the app at `http://localhost:3000` because
Ruitong's S3 CORS config currently allows that origin for direct presigned uploads.

The current Cognito values from A's 2026-06-03 setup are `us-east-1`, user pool
`us-east-1_lb6SisPnD`, and app client `fvmq1uralbq80r9q7nrnonh73`. The API Gateway
prod base URL is `https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod`;
`/upload/presigned` and `/upload/check-dup` are live. Q1/Q2 use D's protected GCP
Cloud Functions root
`https://australia-southeast1-project-e8ee6cc2-5c7b-44f3-aeb.cloudfunctions.net`
with paths `/q1_query_by_tags` and `/q2_query_by_species`.

For Wenxuan's ML service, Q4 must run through API Gateway `/query/by-file`.
B's `/v1/*` token is backend-only and must not appear in frontend code or environment files.

## API Contract Notes

The API client accepts common response shapes used during integration:

- Presigned upload responses can return `uploadUrl`, `upload_url`, `url`,
  `presignedUrl`, or `presigned_url`.
- Presigned upload requests include the SHA-256 `checksum`. Responses can include
  `upload_headers`; the frontend must send those headers unchanged with the S3 `PUT`
  because they are part of the SigV4 signature.
- Duplicate upload checks send the canonical SHA-256 `checksum` field to `/upload/check-dup`.
  A's Lambda still accepts legacy `file_hash`, but the frontend no longer uses it.
- Result lists can be returned as `items`, `results`, `files`, or a raw array.
- Single ML metadata records from B are also accepted, including `file_id`, `file_type`,
  `original_url`, `thumbnail_url`, `tags`, and `predictions`.
- Private S3 keys and raw S3 object URLs returned by query APIs are converted to
  short-lived read URLs through `POST /upload/presigned` before media is displayed.
  The raw storage reference is retained for Q3, Q5, and Q6 requests.
- If a user pastes a presigned S3 thumbnail URL into Q3, the frontend removes the
  temporary signature query string before sending it to `/query/by-thumbnail`.
- Q4 sends uploaded query images to D's API Gateway route as JSON with
  `image_base64`, `filename`, `content_type`, and `limit`.
- Gallery records can include `thumbnail_url`, `thumbnailUrl`, `url`, `original_url`, `originalUrl`, `type`, and `tags`.
- Q3 full-size lookup can return `original_url`, `originalUrl`, `fullUrl`, or `url`.
- Q6 sends one bulk `DELETE /files` request with body `{ "urls": ["<url>", "..."] }`.
- Notifications use `POST /notifications/subscribe` with `action`, `email`, and `species`.
  D also supports `GET /notifications/subscribe?email=<user>` for loading the current subscription list.

All authenticated API calls attach `Authorization: Bearer <token>` using Amplify's current Cognito session.
Q1/Q2 requests therefore carry the same Cognito JWT to GCP, where D's functions verify
the token. The token is used for authentication only; Q1/Q2 return matching records
from the shared DynamoDB database rather than filtering by the logged-in user.

The S3-triggered thumbnail, ML, and database pipeline is asynchronous. Until the team
provides an upload-status endpoint, the upload page previews an uploaded image through a
read URL and reports recognition as queued instead of claiming that tags are already available.

## Build

```bash
cd frontend
npm run build
```

The production artifact is generated in `frontend/dist`, ready for S3 plus CloudFront or Amplify Hosting.

## Deployment

For S3 plus CloudFront hosting, export the deployment bucket and optional distribution ID:

```bash
cd frontend
export VITE_DEPLOY_BUCKET=aussie-ecolens-frontend
export VITE_CLOUDFRONT_DISTRIBUTION_ID=EXAMPLE123
npm run deploy:s3
```

The deploy script builds the Vite app, syncs `dist/` to S3, and invalidates CloudFront when a distribution ID is supplied.
