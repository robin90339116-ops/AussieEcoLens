# D Group Deployment Summary

Deployment date: 2026-06-07

## AWS deployed resources

Region: `us-east-1`

### DynamoDB

- `AussieEcoLensFiles`
  - ARN: `arn:aws:dynamodb:us-east-1:983018774467:table/AussieEcoLensFiles`
  - GSI: `checksum-index`
  - GSI: `owner_id-index`
- `AussieEcoLensNotificationsSub`
  - ARN: `arn:aws:dynamodb:us-east-1:983018774467:table/AussieEcoLensNotificationsSub`

### SNS

- Topic: `AussieEcoLensSpeciesNotifications`
- ARN: `arn:aws:sns:us-east-1:983018774467:AussieEcoLensSpeciesNotifications`

### Lambda

- Q3: `AussieEcoLensD-Q3ThumbnailLookup`
  - ARN: `arn:aws:lambda:us-east-1:983018774467:function:AussieEcoLensD-Q3ThumbnailLookup`
- Q4: `AussieEcoLensD-Q4ImageSearch`
  - ARN: `arn:aws:lambda:us-east-1:983018774467:function:AussieEcoLensD-Q4ImageSearch`
  - Pending from B: `ORACLE_TAG_UPLOAD_URL` and `ORACLE_API_TOKEN`
- Q5: `AussieEcoLensD-Q5UpdateTags`
  - ARN: `arn:aws:lambda:us-east-1:983018774467:function:AussieEcoLensD-Q5UpdateTags`
- Q6: `AussieEcoLensD-Q6DeleteFile`
  - ARN: `arn:aws:lambda:us-east-1:983018774467:function:AussieEcoLensD-Q6DeleteFile`
- Notifications: `AussieEcoLensD-Notifications`
  - ARN: `arn:aws:lambda:us-east-1:983018774467:function:AussieEcoLensD-Notifications`

## A API Gateway integration

API: `EcoLensAPI`

- API ID: `66h13afw3g`
- Stage: `prod`
- Base URL: `https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod`
- Cognito Authorizer: `CognitoAuth`

Attached routes:

- `POST /query/by-thumbnail` -> Q3 Lambda
- `POST /query/by-file` -> Q4 Lambda
- `POST /tags/modify` -> Q5 Lambda
- `DELETE /files` -> Q6 Lambda
- `GET /notifications/subscribe` -> notifications Lambda
- `POST /notifications/subscribe` -> notifications Lambda

Internal API Gateway test invoke results:

- `POST /query/by-thumbnail`: Lambda reached, returned expected validation error for missing `thumbnail_url`
- `POST /query/by-file`: Lambda reached, returned expected validation error for missing file
- `POST /tags/modify`: Lambda reached, returned expected validation error for missing `urls`
- `DELETE /files`: Lambda reached, returned expected validation error for missing target
- `GET /notifications/subscribe`: Lambda reached, returned `{"subscriptions": []}`
- `POST /notifications/subscribe`: Lambda reached, returned expected validation error for missing action

## Frontend URLs for C

Use the same base URL with Cognito JWT:

- Q3: `POST https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/query/by-thumbnail`
- Q4: `POST https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/query/by-file`
- Q5: `POST https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/tags/modify`
- Q6: `DELETE https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/files`
- Notifications list: `GET https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/notifications/subscribe`
- Notifications subscribe/unsubscribe: `POST https://66h13afw3g.execute-api.us-east-1.amazonaws.com/prod/notifications/subscribe`

## Still pending

- GCP Q1/Q2 real deployment is not done on this machine because there is no `gcloud` CLI, Google login, project ID, or service account credentials available.
  - Deployment script is ready: `scripts/deploy_gcp_q1_q2.sh`
  - Validation script is ready: `scripts/check_gcp_q1_q2.sh`
  - Required values: `GCP_PROJECT`, fresh `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`
  - Cognito defaults in the script: `COGNITO_USER_POOL_ID=us-east-1_lb6SisPnD`, `COGNITO_APP_CLIENT_ID=fvmq1uralbq80r9q7nrnonh73`
- Q4 real Oracle tagging call is deployed but needs B to provide `ORACLE_TAG_UPLOAD_URL` and `ORACLE_API_TOKEN`, then update the Q4 Lambda environment.
- AWS Academy credentials are temporary. If deployment or GCP DynamoDB access fails later, refresh the Lab credentials and update runtime environment variables.
