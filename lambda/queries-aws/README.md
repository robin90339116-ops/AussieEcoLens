# AWS query Lambdas

These handlers cover D group's AWS-side query and management APIs:

- `q3_thumbnail_lookup`: thumbnail URL to original media URL lookup.
- `q4_image_search`: receive C's query file upload, call B's Oracle tagging endpoint, then query by returned tags without storing the query image.
- `q5_update_tags`: batch add/remove tags.
- `q6_delete_file`: delete original object, thumbnail object, and DynamoDB record.

Formal demo integration rule:

- These Lambda handlers must be attached to A's API Gateway with Cognito Authorizer.
- Frontend should call A's API Gateway, not these Lambda functions directly.
- B's Oracle token must remain in Lambda environment variables. Frontend must not receive it.

Package each function with `Project/lambda/shared` on the Python path or publish
`lambda/shared` as a Lambda layer under `/opt/python`.

Required environment variables:

- `FILES_TABLE`, default `AussieEcoLensFiles`
- `AWS_REGION`, default `us-east-1`
- `ORIGINAL_BUCKET`, required only when records store `original_s3_key`
- `THUMBNAIL_BUCKET`, required only when records store `thumbnail_s3_key`
- `ORACLE_TAG_UPLOAD_URL`, required for formal Q4
- `ORACLE_API_TOKEN`, required for formal Q4
- `ORACLE_TIMEOUT_SECONDS`, optional for Q4
- `ML_QUERY_LAMBDA_NAME`, legacy fallback only for image URL requests
- `CORS_ALLOW_ORIGIN`, default `*`
