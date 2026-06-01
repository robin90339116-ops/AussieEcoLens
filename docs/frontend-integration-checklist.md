# Frontend Integration Checklist

Use this checklist before the final demo. It is not report text; it is a practical handover list for connecting the React UI to the team services.

## Required Environment Values

| Variable | Owner | Purpose |
| --- | --- | --- |
| `VITE_AWS_REGION` | A | Cognito and API region |
| `VITE_COGNITO_USER_POOL_ID` | A | Cognito User Pool used by Amplify Auth |
| `VITE_COGNITO_CLIENT_ID` | A | Cognito App Client ID |
| `VITE_AWS_API_BASE_URL` | A/D | API Gateway root for AWS-side endpoints |
| `VITE_GCP_API_BASE_URL` | D | GCP Cloud Functions root for Q1/Q2 |
| `VITE_USE_MOCKS=false` | C | Must be false for real integration and demo |

## Backend Contract Checks

Confirm these request and response shapes with A and D before demo:

- Presigned upload: frontend sends `fileName`, `contentType`, and `size`; response must include `uploadUrl`, `url`, or `presignedUrl`.
- Upload status: confirm whether `/files/status` exists. If not, replace `VITE_UPLOAD_STATUS_PATH` or adjust `pollUploadStatus`.
- Q1 tag count query: confirm whether backend expects `{ tags: { species: count } }` or the raw `{ species: count }` object.
- Q2 species query: confirm whether backend expects `{ species: "dingo" }`, query params, or a path parameter.
- Q3 thumbnail lookup: confirm request body key is `thumbnail_url` and response includes `original_url`, `originalUrl`, `fullUrl`, or `url`.
- Q4 uploaded-file query: confirm multipart field name is `file` and the uploaded query image is not permanently stored.
- Q5 bulk tag edit: confirm request body is `{ urls, tags, operation }` with `operation` as `1` for add and `0` for remove.
- Q6 delete files: confirm request body is `{ urls }` and backend deletes storage objects and database records.
- Subscriptions: confirm request body for save is `{ species: [...] }`, and cancel supports DELETE with `{ species }`.

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

