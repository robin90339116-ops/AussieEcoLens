# D group API Gateway handoff

This folder is for A group integration only. It does not deploy a standalone API.

Use `d-group-openapi-fragment.yaml` as a route map when attaching D group's AWS
Lambda handlers to A's API Gateway.

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
- B's ML Lambda remains private and is called only by Q4 through
  `ML_QUERY_LAMBDA_NAME`.
- GCP Q1/Q2 can either be routed through A's API Gateway or exposed directly as
  protected HTTPS endpoints with Cognito JWT verification enabled.

