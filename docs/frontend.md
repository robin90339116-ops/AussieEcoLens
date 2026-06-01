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
| `/upload` | Media selection, presigned URL upload, progress, processing status | `GET /presigned-url`, S3 `PUT`, optional `/files/status` |
| `/search` | Q1 tag-count AND query, Q2 species query, Q4 uploaded-file query | GCP Q1/Q2, AWS Q4 |
| `/results` | Thumbnail/video gallery and Q3 full-size lookup | AWS Q3 |
| `/tag-manage` | Q5 bulk add/remove tags | AWS Q5 |
| `/delete` | Q6 multi-select deletion with confirmation | AWS Q6 |
| `/subscribe` | Tag subscription and cancellation | AWS subscription API |

## Configuration

Copy `frontend/.env.example` to `frontend/.env` and fill in the values supplied by the team:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Set `VITE_USE_MOCKS=false` when real AWS/GCP endpoints are available.

## API Contract Notes

The API client accepts common response shapes used during integration:

- Presigned upload responses can return `uploadUrl`, `url`, or `presignedUrl`.
- Result lists can be returned as `items`, `results`, `files`, or a raw array.
- Gallery records can include `thumbnail_url`, `thumbnailUrl`, `url`, `original_url`, `originalUrl`, `type`, and `tags`.
- Q3 full-size lookup can return `original_url`, `originalUrl`, `fullUrl`, or `url`.

All authenticated API calls attach `Authorization: Bearer <token>` using Amplify's current Cognito session.

## Build

```bash
cd frontend
npm run build
```

The production artifact is generated in `frontend/dist`, ready for S3 plus CloudFront or Amplify Hosting.
