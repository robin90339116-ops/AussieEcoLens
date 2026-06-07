# GCP Cloud Functions for Q1 and Q2

This directory is self-contained for deploying D group's GCP APIs.

Formal demo integration rule:

- Prefer routing Q1/Q2 through A's API Gateway so the frontend has one backend entry point.
- If Q1/Q2 are exposed directly from GCP, they must be public HTTPS endpoints protected by Cognito JWT verification.
- Do not set `AUTH_REQUIRED=false` outside local smoke tests.

Functions:

- `q1_query_by_tags`: Q1 AND query by species counts.
- `q2_query_by_species`: Q2 query by species existence.

Required environment variables:

- `AWS_REGION`: AWS DynamoDB region, default `us-east-1`.
- `FILES_TABLE`: DynamoDB files table, default `AussieEcoLensFiles`.
- `COGNITO_REGION`: Cognito region. Use `us-east-1` for the current team setup unless A confirms otherwise.
- `COGNITO_USER_POOL_ID`: Cognito user pool id.
- `COGNITO_APP_CLIENT_ID`: Cognito app client id.
- `AUTH_REQUIRED`: set `false` only for local smoke tests.
- `CORS_ALLOW_ORIGIN`: frontend origin list, default `http://localhost:3000`.
- `PRESIGN_MEDIA_URLS`: keep `true` so private S3 media is returned as short-lived presigned GET URLs.
- `PRESIGNED_URL_EXPIRES_SECONDS`: default `900`.

GCP must have AWS credentials available through Secret Manager or environment
variables so `boto3` can read DynamoDB.

If using AWS Academy credentials, refresh the GCP environment variables before
each demo or integration session because the session credentials expire.

Deploy examples:

```bash
gcloud functions deploy q1_query_by_tags \
  --gen2 \
  --runtime=python312 \
  --region=australia-southeast1 \
  --source=Project/gcp-functions/queries-gcp \
  --entry-point=q1_query_by_tags \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=AWS_REGION=us-east-1,FILES_TABLE=AussieEcoLensFiles,COGNITO_REGION=us-east-1,COGNITO_USER_POOL_ID=YOUR_POOL_ID,COGNITO_APP_CLIENT_ID=YOUR_CLIENT_ID,AUTH_REQUIRED=true,CORS_ALLOW_ORIGIN=http://localhost:3000

gcloud functions deploy q2_query_by_species \
  --gen2 \
  --runtime=python312 \
  --region=australia-southeast1 \
  --source=Project/gcp-functions/queries-gcp \
  --entry-point=q2_query_by_species \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=AWS_REGION=us-east-1,FILES_TABLE=AussieEcoLensFiles,COGNITO_REGION=us-east-1,COGNITO_USER_POOL_ID=YOUR_POOL_ID,COGNITO_APP_CLIENT_ID=YOUR_CLIENT_ID,AUTH_REQUIRED=true,CORS_ALLOW_ORIGIN=http://localhost:3000
```

`--allow-unauthenticated` only makes the HTTPS trigger reachable. Application-level Cognito JWT verification still protects the function when `AUTH_REQUIRED=true`.
