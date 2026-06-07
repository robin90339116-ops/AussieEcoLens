# D group API Gateway handoff

This folder is for A group integration only. It does not deploy a standalone API.

Use `d-group-openapi-fragment.yaml` as a route map when attaching D group's AWS
Lambda handlers to A's API Gateway.

Final path mapping agreed for the frontend:

- `POST /query/by-thumbnail` -> `q3_thumbnail_lookup`
- `POST /query/by-file` -> `q4_image_search`
- `POST /tags/modify` -> `q5_update_tags`
- `DELETE /files` -> `q6_delete_file`
- `GET/POST /notifications/subscribe` -> `notifications`

Required A-side values:

- `AWS_REGION`
- `COGNITO_USER_POOL_ID`
- `COGNITO_APP_CLIENT_ID`
- `Q3_THUMBNAIL_LOOKUP_LAMBDA_ARN`
- `Q4_IMAGE_SEARCH_LAMBDA_ARN`
- `Q5_UPDATE_TAGS_LAMBDA_ARN`
- `Q6_DELETE_FILE_LAMBDA_ARN`
- `NOTIFICATIONS_LAMBDA_ARN`

Formal demo boundary:

- Frontend should call A's API Gateway.
- D's Q3/Q4/Q5/Q6 and notification Lambdas sit behind A's API Gateway.
- B's Oracle tagging endpoint remains private behind backend services. Q4 calls
  it with `ORACLE_TAG_UPLOAD_URL` and `ORACLE_API_TOKEN`.
- GCP Q1/Q2 can either be routed through A's API Gateway or exposed directly as
  protected HTTPS endpoints with Cognito JWT verification enabled.

Package the five D Lambdas with:

```bash
./scripts/package_d_lambdas.sh
```

The generated zip files include the handler and `lambda/shared` helper files.
