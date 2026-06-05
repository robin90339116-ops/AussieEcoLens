# GCP Cloud Functions for Q1 and Q2

This directory is self-contained for deploying D group's GCP APIs.

Functions:

- `q1_query_by_tags`: Q1 AND query by species counts.
- `q2_query_by_species`: Q2 query by species existence.

Required environment variables:

- `AWS_REGION`: AWS DynamoDB region, default `ap-southeast-2`.
- `FILES_TABLE`: DynamoDB files table, default `AussieEcoLensFiles`.
- `COGNITO_REGION`: Cognito region.
- `COGNITO_USER_POOL_ID`: Cognito user pool id.
- `COGNITO_APP_CLIENT_ID`: Cognito app client id.
- `AUTH_REQUIRED`: set `false` only for local smoke tests.
- `CORS_ALLOW_ORIGIN`: frontend origin, default `*`.

GCP must have AWS credentials available through Secret Manager or environment
variables so `boto3` can read DynamoDB.

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
  --set-env-vars=AWS_REGION=ap-southeast-2,FILES_TABLE=AussieEcoLensFiles,COGNITO_REGION=ap-southeast-2,COGNITO_USER_POOL_ID=YOUR_POOL_ID,COGNITO_APP_CLIENT_ID=YOUR_CLIENT_ID

gcloud functions deploy q2_query_by_species \
  --gen2 \
  --runtime=python312 \
  --region=australia-southeast1 \
  --source=Project/gcp-functions/queries-gcp \
  --entry-point=q2_query_by_species \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars=AWS_REGION=ap-southeast-2,FILES_TABLE=AussieEcoLensFiles,COGNITO_REGION=ap-southeast-2,COGNITO_USER_POOL_ID=YOUR_POOL_ID,COGNITO_APP_CLIENT_ID=YOUR_CLIENT_ID
```

