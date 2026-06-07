# AWS query Lambdas

These handlers cover D group's AWS-side query and management APIs:

- `q3_thumbnail_lookup`: thumbnail URL to original media URL lookup, with presigned access URLs for private S3 media.
- `q4_image_search`: receive C's query file upload, call B's Oracle tagging endpoint, then query by returned tags without storing the query image.
- `q5_update_tags`: batch add/remove tags.
- `q6_delete_file`: delete original object, thumbnail object, and DynamoDB record.

Formal demo integration rule:

- These Lambda handlers must be attached to A's API Gateway with Cognito Authorizer.
- Frontend should call A's API Gateway, not these Lambda functions directly.
- B's Oracle token must remain in Lambda environment variables. Frontend must not receive it.

Package all five D Lambdas from the repository root:

```bash
./scripts/package_d_lambdas.sh
```

The generated zip files copy `lambda/shared` into each handler package.

Required environment variables:

- `FILES_TABLE`, default `AussieEcoLensFiles`
- `AWS_REGION`, default `us-east-1`
- `ORIGINAL_BUCKET`, required only when records store `original_s3_key`
- `THUMBNAIL_BUCKET`, required only when records store `thumbnail_s3_key`
- `PRESIGN_MEDIA_URLS`, default `true`
- `PRESIGNED_URL_EXPIRES_SECONDS`, default `900`
- `ORACLE_TAG_UPLOAD_URL`, required for formal Q4
- `ORACLE_API_TOKEN`, required for formal Q4
- `ORACLE_TIMEOUT_SECONDS`, optional for Q4
- `ML_QUERY_LAMBDA_NAME`, legacy fallback only for image URL requests
- `CORS_ALLOW_ORIGIN`, default `http://localhost:3000` when configured for frontend demo

Frontend routes through A API Gateway:

- Q3: `POST /query/by-thumbnail`
- Q4: `POST /query/by-file`
- Q5: `POST /tags/modify`
- Q6: `DELETE /files`
