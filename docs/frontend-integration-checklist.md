# Frontend Integration Checklist

Use this checklist before the final demo. It is not report text; it is a practical handover list for connecting the React UI to the team services.

## Required Environment Values

| Variable | Owner | Purpose |
| --- | --- | --- |
| `VITE_AWS_REGION=us-east-1` | A | Cognito and API Gateway region from Ruitong's setup |
| `VITE_COGNITO_USER_POOL_ID=us-east-1_lb6SisPnD` | A | Cognito User Pool used by Amplify Auth |
| `VITE_COGNITO_CLIENT_ID=fvmq1uralbq80r9q7nrnonh73` | A | Public SPA App Client ID; no client secret |
| `VITE_AWS_API_BASE_URL=https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod` | A | API Gateway prod invoke URL for live upload endpoints |
| `VITE_GCP_API_BASE_URL` | D | Optional separate GCP Cloud Functions root for Q1/Q2; leave empty if API Gateway routes them |
| `VITE_ML_API_BASE_URL` | B | Optional direct root for Wenxuan's ML upload-tagging service |
| `VITE_ML_UPLOAD_PATH=/v1/tag/upload` | B | Direct ML route for Q4 when API Gateway does not proxy `/query/by-file` |
| `VITE_USE_MOCKS=false` | C | Must be false for real integration and demo |

## API Gateway Paths From A

Ruitong's 2026-06-03 package confirms the API Gateway resource tree, but also states that methods are not created yet. The frontend path defaults now match these resources:

| Feature | Frontend variable | Confirmed path |
| --- | --- | --- |
| Presigned upload | `VITE_PRESIGNED_PATH` | `/upload/presigned` |
| Duplicate check | `VITE_UPLOAD_CHECK_DUP_PATH` | `/upload/check-dup` |
| Q1 tag-count query | `VITE_Q1_PATH` | `/query/by-tags` |
| Q2 species query | `VITE_Q2_PATH` | `/query/by-species` |
| Q3 thumbnail lookup | `VITE_Q3_PATH` | `/query/by-thumbnail` |
| Q4 uploaded-file query | `VITE_Q4_PATH` | `/query/by-file` |
| Q5 tag edit | `VITE_Q5_PATH` | `/tags/modify` |
| Q6 file delete/list | `VITE_Q6_PATH`, `VITE_LIST_FILES_PATH` | `/files` |
| Subscriptions | `VITE_SUBSCRIPTIONS_PATH` | `/notifications/subscribe` |

## Upload Interface From A

Ruitong's branch adds Lambda code for presigned upload and duplicate checking:

- `POST /upload/check-dup` is live on prod and sends `{ "file_hash": "<md5>" }`.
- Duplicate response uses HTTP `409` with `{ "duplicate": true, "message": "...", "existing_file": "<url>" }`.
- Non-duplicate response uses HTTP `200` with `{ "duplicate": false }`.
- `POST /upload/presigned` is live on prod and sends `{ "action": "PUT", "filename": "...", "content_type": "...", "file_hash": "..." }`.
- Presigned upload response is `{ "upload_url": "...", "file_key": "...", "bucket": "aussie-ecolens-35346906" }`.
- The same presigned Lambda can generate read URLs with `{ "action": "GET", "s3_url": "..." }` or `{ "action": "GET", "file_key": "..." }`, returning `{ "presigned_url": "..." }`.
- The frontend computes MD5 in the browser before requesting the upload URL, then uploads the file to S3 using `PUT`.
- Ruitong's S3 CORS config currently allows `http://localhost:3000`, so the Vite dev server is configured to use port `3000` for local integration.

## ML Interface From B

Wenxuan's branch confirms the B module metadata shape. The frontend now accepts both lists of files and a single metadata object:

- Stored upload/ML metadata includes `file_id`, `file_type`, `original_url`, `thumbnail_url`, `tags`, `predictions`, and `created_at`.
- Tags are common species names mapped to counts, for example `{ "dingo": 1 }`.
- The direct query-by-file ML service endpoint is `POST /v1/tag/upload` with multipart field `file`; it returns detected `tags` and `predictions` without permanently storing the query image.
- The API Gateway `/query/by-file` route should either return matched stored files from D, or return this B metadata object so the UI can show detected tags.
- The frontend now supports both options: if `VITE_ML_API_BASE_URL` is set, Q4 posts directly to B; otherwise Q4 posts to API Gateway `/query/by-file`.

## Backend Contract Checks

Confirm these methods, request bodies, and response shapes with A and D before demo:

- API Gateway deployment: upload endpoints are confirmed on the prod stage; confirm whether the remaining query/tag/delete/notification methods are also deployed there.
- Presigned upload: A's Lambda currently expects `POST` with `filename`, `content_type`, and optional `file_hash`; response includes `upload_url`, `file_key`, and `bucket`.
- Duplicate check: A's Lambda currently expects `POST /upload/check-dup` with an MD5 `file_hash`.
- Upload status/result: Ruitong's resource tree has no status endpoint yet. If A adds one, set `VITE_UPLOAD_STATUS_PATH`; otherwise the frontend completes upload with basic file metadata.
- Q1 tag count query: confirm whether backend expects `{ tags: { species: count } }` or the raw `{ species: count }` object.
- Q2 species query: confirm whether backend expects `{ species: "dingo" }`, query params, or a path parameter.
- Q3 thumbnail lookup: confirm request body key is `thumbnail_url` and response includes `original_url`, `originalUrl`, `fullUrl`, or `url`.
- Q4 uploaded-file query: confirm multipart field name is `file`. Wenxuan's B endpoint returns detected tags without storing the file; confirm whether D then returns matched stored files or the gateway returns only the B metadata. If API Gateway is not ready, set `VITE_ML_API_BASE_URL` to B's service root for direct testing.
- Q5 bulk tag edit: confirm request body is `{ urls, tags, operation }` with `operation` as `1` for add and `0` for remove.
- Q6 delete files: frontend currently posts `{ urls }` to `/files`; confirm whether A implements this as `POST /files`, `DELETE /files`, or another method.
- File listing: frontend currently reads `GET /files`; confirm the response returns `items`, `results`, `files`, or an array.
- Subscriptions: frontend uses `GET`, `POST { species: [...] }`, and `DELETE { species }` against `/notifications/subscribe`; confirm methods and body keys.

## Demo Smoke Test

1. Set `VITE_USE_MOCKS=false`.
2. Run `npm run build`.
3. Start `npm run dev` or open the deployed URL.
4. Register a new user, verify email, sign in, and sign out.
5. Confirm protected routes redirect unauthenticated users to `/login`.
6. Upload one image and verify progress, upload success, thumbnail, and tags.
7. Run Q1 with two species/count rows and confirm AND semantics.
8. Run Q2 for one species.
9. Run Q4 with a query image and confirm the query image is not stored.
10. Click a thumbnail and confirm Q3 returns the full-size image URL.
11. Add and remove a tag for multiple URLs.
12. Delete a file and confirm it disappears from the UI.
13. Subscribe and unsubscribe from one species.
