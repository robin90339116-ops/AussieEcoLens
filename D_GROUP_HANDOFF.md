# D group API handoff

This branch contains the urgent D group API work for AussieEcoLens.

## What is included

- DynamoDB schema and CloudFormation template:
  - `infra/dynamodb/schema.md`
  - `infra/dynamodb/template.yaml`
- SNS topic template:
  - `infra/sns/template.yaml`
- Shared helper package for A/B/D:
  - `lambda/shared/aussie_ecolens_db.py`
  - `lambda/shared/sns_helpers.py`
- AWS Lambda handlers:
  - Q3 thumbnail URL to original URL lookup
  - Q4 query image search, calling B's ML Lambda and not storing the query image
  - Q5 batch add/remove tags
  - Q6 delete file from S3 and DynamoDB
  - notification subscribe/unsubscribe/publish helper
- GCP Cloud Functions:
  - Q1 tag + count AND query
  - Q2 species query
  - Cognito JWT verification and CORS
- API contract and curl examples:
  - `docs/db-and-queries.md`

## For teammates

Frontend should start from `docs/db-and-queries.md`.

For the formal frontend demo, the preferred route is:

1. Frontend calls only A's API Gateway endpoints.
2. A's API Gateway uses Cognito Authorizer.
3. A's API Gateway routes D's AWS Lambda handlers for Q3/Q4/Q5/Q6 and notifications.
4. B's ML Lambda stays behind backend services and is not called directly by the frontend.

D's GCP Q1/Q2 endpoints are the only exception. If they are not routed through A's API Gateway, they must be public HTTPS endpoints protected by the included Cognito JWT verification middleware.

B can import `lambda/shared/aussie_ecolens_db.py` to write records after ML tagging, and can call the notification publish helper after a new record is stored.

C can use the documented Q1/Q2/Q3/Q4/Q5/Q6 request and response formats to wire the UI, but should confirm whether Q1/Q2 are exposed through A's API Gateway or directly through the protected GCP HTTPS URLs.

## Still needed before final demo

- Real AWS/GCP deployment using team credentials.
- A's Cognito values:
  - `COGNITO_USER_POOL_ID`
  - `COGNITO_APP_CLIENT_ID`
  - `COGNITO_REGION`
- B's ML query Lambda name for Q4:
  - `ML_QUERY_LAMBDA_NAME`
- Final endpoint URLs pasted back into `docs/db-and-queries.md`.
- Final team report, individual report, and architecture figure.
