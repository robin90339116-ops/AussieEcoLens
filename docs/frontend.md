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
| `/search` | Q1 tag-count AND query, Q2 species query, Q4 uploaded-file query | `/query/by-tags`, `/query/by-species`, `/query/by-file` |
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
`/upload/presigned` and `/upload/check-dup` are live, while the remaining
query/tag/delete/notification methods still need final deployed endpoint confirmation before the demo.

For Wenxuan's ML service, Q4 must run through API Gateway `/query/by-file`.
B's `/v1/*` token is backend-only and must not appear in frontend code or environment files.

## API Contract Notes

The API client accepts common response shapes used during integration:

- Presigned upload responses can return `uploadUrl`, `upload_url`, `url`,
  `presignedUrl`, or `presigned_url`.
- Duplicate upload checks send a SHA-256 `file_hash` and `checksum` to `/upload/check-dup`.
- Result lists can be returned as `items`, `results`, `files`, or a raw array.
- Single ML metadata records from B are also accepted, including `file_id`, `file_type`,
  `original_url`, `thumbnail_url`, `tags`, and `predictions`.
- Q4 sends uploaded query images to D's API Gateway route as JSON with `image_base64`, `content_type`, and `limit`.
- Gallery records can include `thumbnail_url`, `thumbnailUrl`, `url`, `original_url`, `originalUrl`, `type`, and `tags`.
- Q3 full-size lookup can return `original_url`, `originalUrl`, `fullUrl`, or `url`.
- Q6 deletes each selected file with `DELETE /files` and body `{ "url": "<original_or_thumbnail_url>" }`.
- Notifications use `POST /notifications/subscribe` with `action`, `user_email`, and `species_list`.
  D does not currently expose a GET subscription-list endpoint, so the UI keeps a browser-local cache only for display.

All authenticated API calls attach `Authorization: Bearer <token>` using Amplify's current Cognito session.

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
