# Frontend Integration Checklist

Use this checklist before the final demo. It is not report text; it is a practical handover list for connecting the React UI to the team services.

## Required Environment Values

| Variable | Owner | Purpose |
| --- | --- | --- |
| `VITE_AWS_REGION=us-east-1` | A | Cognito and API Gateway region from Ruitong's setup |
| `VITE_COGNITO_USER_POOL_ID=us-east-1_lb6SisPnD` | A | Cognito User Pool used by Amplify Auth |
| `VITE_COGNITO_CLIENT_ID=fvmq1uralbq80r9q7nrnonh73` | A | Public SPA App Client ID; no client secret |
| `VITE_AWS_API_BASE_URL=https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod` | A | API Gateway prod invoke URL for live upload endpoints |
| `VITE_GCP_API_BASE_URL=https://australia-southeast1-project-e8ee6cc2-5c7b-44f3-aeb.cloudfunctions.net` | D | Protected GCP Cloud Functions root for Q1/Q2 |
| `VITE_USE_MOCKS=false` | C | Must be false for real integration and demo |

## API Gateway Paths From A

Ruitong's 2026-06-03 package confirms the API Gateway resource tree, but also states that methods are not created yet. The frontend path defaults now match these resources:

| Feature | Frontend variable | Confirmed path |
| --- | --- | --- |
| Presigned upload | `VITE_PRESIGNED_PATH` | `/upload/presigned` |
| Duplicate check | `VITE_UPLOAD_CHECK_DUP_PATH` | `/upload/check-dup` |
| Q1 tag-count query | `VITE_Q1_PATH` | `/q1_query_by_tags` |
| Q2 species query | `VITE_Q2_PATH` | `/q2_query_by_species` |
| Q3 thumbnail lookup | `VITE_Q3_PATH` | `/query/by-thumbnail` |
| Q4 uploaded-file query | `VITE_Q4_PATH` | `/query/by-file` |
| Q5 tag edit | `VITE_Q5_PATH` | `/tags/modify` |
| Q6 file delete | `VITE_Q6_PATH` | `/files` |
| Optional file list | `VITE_LIST_FILES_PATH` | Empty until A/D expose a GET list endpoint |
| Subscriptions | `VITE_SUBSCRIPTIONS_PATH` | `/notifications/subscribe` |

## Upload Interface From A

Ruitong's branch adds Lambda code for presigned upload and duplicate checking:

- `POST /upload/check-dup` is live on prod and sends `{ "checksum": "<sha256>" }`.
  A's Lambda also accepts the legacy `file_hash` field for compatibility.
- Duplicate response uses HTTP `409` with `{ "duplicate": true, "message": "...", "existing_file": "<url>" }`.
- Non-duplicate response uses HTTP `200` with `{ "duplicate": false }`.
- `POST /upload/presigned` is live on prod and sends
  `{ "filename": "...", "content_type": "...", "checksum": "<sha256>" }`.
- Presigned upload response is `{ "upload_url": "...", "file_key": "...", "bucket": "aussie-ecolens-35346906" }`.
- The response may also include
  `{ "upload_headers": { "x-amz-meta-owner-id": "<cognito owner>" } }`.
  These headers are signed and must be included unchanged in the direct S3 `PUT`.
- The same presigned Lambda can generate read URLs with `{ "action": "GET", "s3_url": "..." }` or `{ "action": "GET", "file_key": "..." }`, returning `{ "presigned_url": "..." }`.
- Query responses may contain private S3 keys or raw object URLs. The frontend extracts
  the object key, requests a short-lived GET URL from this Lambda for display, and keeps
  the raw reference for later Q3/Q5/Q6 requests.
- Q3 accepts the stored thumbnail URL. If a copied thumbnail URL contains an
  `X-Amz-Signature` query string, the frontend strips the temporary query parameters
  before calling `/query/by-thumbnail`.
- The frontend computes SHA-256 in the browser before requesting the upload URL, then uploads the file to S3 using `PUT`.
- Ruitong's S3 CORS config currently allows `http://localhost:3000`, so the Vite dev server is configured to use port `3000` for local integration.

## ML Interface From B

Wenxuan's branch confirms the B module metadata shape. The frontend now accepts both lists of files and a single metadata object:

- Stored upload/ML metadata includes `file_id`, `file_type`, `original_url`, `thumbnail_url`, `tags`, `predictions`, and `created_at`.
- Tags are common species names mapped to counts, for example `{ "dingo": 1 }`.
- B's direct query-by-file ML service endpoint is `POST /v1/tag/upload`, but the frontend must not call it directly.
- Wenxuan's PDF says all `/v1/*` routes require `Authorization: Bearer <API_AUTH_TOKEN>`, and that token must not be hardcoded or exposed in frontend code.
- D's API Gateway `/query/by-file` route expects `image_base64` JSON, calls B's ML Lambda for tags, and returns matched stored files from DynamoDB.
- The frontend has no `VITE_ML_API_BASE_URL` setting. Q4 always posts to API Gateway `/query/by-file`.

## D Branch Contract Checks

These methods and body shapes were read from `origin/Lianjun-Zhang`:

- API Gateway deployment: upload endpoints are confirmed on A's prod stage; confirm whether Q3/Q4/Q5/Q6 and notifications are now deployed there.
- Presigned upload: A's Lambda expects `POST` with `filename`, `content_type`, and
  SHA-256 `checksum`; response includes `upload_url`, `file_key`, `bucket`, and
  optional signed `upload_headers`.
- Duplicate check: A's Lambda expects `POST /upload/check-dup` with the SHA-256 `checksum` field; legacy `file_hash` is also accepted.
- Upload status/result: Ruitong's resource tree has no status endpoint yet. If A adds one,
  set `VITE_UPLOAD_STATUS_PATH`; otherwise the frontend reports recognition as queued.
- Q1 tag count query: D's deployed GCP handler is
  `https://australia-southeast1-project-e8ee6cc2-5c7b-44f3-aeb.cloudfunctions.net/q1_query_by_tags`;
  it expects `POST` JSON `{ tags: { species: count }, limit }`, verifies Cognito JWTs, searches the shared database, and returns `items`.
- Q2 species query: D's deployed GCP handler is
  `https://australia-southeast1-project-e8ee6cc2-5c7b-44f3-aeb.cloudfunctions.net/q2_query_by_species`;
  it expects `POST` JSON `{ species, limit }`, verifies Cognito JWTs, searches the shared database, and returns `items`.
- Q3 thumbnail lookup: D's AWS Lambda expects `POST` JSON `{ thumbnail_url }` and returns `original_url`, `thumbnail_url`, `tags`, and `type`.
- Q4 uploaded-file query: D's AWS Lambda expects `POST` JSON
  `{ image_base64, filename, content_type, limit }` or `{ image_url, limit }`;
  it calls B's ML service and does not store the query image.
- Q5 bulk tag edit: D's AWS Lambda expects `POST` JSON `{ urls, tags, operation }` with `operation` as `add/1` or `remove/0`.
- Q6 delete files: D's AWS Lambda accepts bulk `DELETE` JSON `{ urls: [...] }`
  or `{ file_ids: [...] }`. The frontend sends one bulk request for all selected URLs.
- File listing: D's branch does not include a GET list endpoint. The frontend leaves `VITE_LIST_FILES_PATH` empty unless A/D add one.
- Subscriptions: D's AWS Lambda supports `GET ?email=<user>` for listing and `POST` actions for subscribe/unsubscribe.
  A must attach both GET and POST methods to the agreed API Gateway path.
- Path coordination: A and D now use the agreed `/notifications/subscribe` path for subscription list, subscribe and unsubscribe.

## Demo Smoke Test

1. Set `VITE_USE_MOCKS=false`.
2. Run `npm run build`.
3. Start `npm run dev` or open the deployed URL.
4. Register a new user, verify email, sign in, and sign out.
5. Confirm protected routes redirect unauthenticated users to `/signup`.
6. Upload one image and verify progress and the uploaded-image preview. If no status
   endpoint is deployed, confirm the page says `Recognition queued`; otherwise also
   verify the generated thumbnail and tags.
7. Run Q1 with two species/count rows and confirm AND semantics. The request must
   include a Cognito JWT, but matching files are returned from the shared database,
   not only from the current user's uploads.
8. Run Q2 for one species and confirm the browser Network request goes to the
   `cloudfunctions.net` domain with an `Authorization: Bearer ...` header.
9. Run Q4 with a query image and confirm the query image is not stored.
10. Run Q3 from the thumbnail URL tab, then click a result thumbnail and confirm the
    full-size image opens.
11. Add and remove a tag for multiple URLs.
12. Delete a file and confirm it disappears from the UI.
13. Subscribe and unsubscribe from one species.
