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
  - Q3 thumbnail URL to original URL lookup, returning presigned media access URLs
  - Q4 query file search, calling B's Oracle tagging endpoint and not storing the query image
  - Q5 batch add/remove tags
  - Q6 delete file from S3 and DynamoDB
  - notification subscribe/unsubscribe/list/publish helper with SNS subscription ARN tracking
- GCP Cloud Functions:
  - Q1 tag + count AND query
  - Q2 species query
  - Cognito JWT verification and CORS
- API contract and curl examples:
  - `docs/db-and-queries.md`
- Demo and architecture support docs:
  - `docs/demo-checklist.md`
  - `docs/architecture.md`
- A API Gateway route handoff:
  - `infra/api-gateway/d-group-openapi-fragment.yaml`
  - `infra/api-gateway/README.md`
- Local checks:
  - `tests/smoke_d_group.py`
  - `tests/test_d_group_handlers.py`

## For teammates

Frontend should start from `docs/db-and-queries.md`.

For the formal frontend demo, the preferred route is:

1. Frontend calls only A's API Gateway endpoints.
2. A's API Gateway uses Cognito Authorizer.
3. A's API Gateway routes D's AWS Lambda handlers for Q3/Q4/Q5/Q6 and notifications.
4. B's Oracle tagging token stays behind backend services and is not exposed to the frontend.

D's GCP Q1/Q2 endpoints are the only exception. If they are not routed through A's API Gateway, they must be public HTTPS endpoints protected by the included Cognito JWT verification middleware.

B can import `lambda/shared/aussie_ecolens_db.py` to write records after ML tagging, and can call the notification publish helper after a new record is stored.

C can use the documented Q1/Q2/Q3/Q4/Q5/Q6 request and response formats to wire the UI, but should confirm whether Q1/Q2 are exposed through A's API Gateway or directly through the protected GCP HTTPS URLs.

Final AWS-side paths for A/C integration:

- `POST /query/by-thumbnail` -> Q3
- `POST /query/by-file` -> Q4
- `POST /tags/modify` -> Q5
- `DELETE /files` -> Q6
- `GET/POST /notifications/subscribe` -> notification list/subscribe/unsubscribe/publish

Query responses include short-lived `original_access_url` and `thumbnail_access_url`
fields for private S3 media. The original stored values are retained in
`original_raw_url` and `thumbnail_raw_url` when signing succeeds.

## Still needed before final demo

- Real AWS/GCP deployment using team credentials.
- A's Cognito values:
  - `COGNITO_USER_POOL_ID`
  - `COGNITO_APP_CLIENT_ID`
  - `COGNITO_REGION`
- B's Oracle tagging values for Q4:
  - `ORACLE_TAG_UPLOAD_URL`
  - `ORACLE_API_TOKEN`
- Final endpoint URLs pasted back into `docs/db-and-queries.md`.
- Run `scripts/package_d_lambdas.sh` before AWS Lambda upload so each zip includes `lambda/shared`.
- Final team report and individual report.
- Final architecture figure redraw with official AWS/GCP icons if required.

## Local verification

```bash
/Users/whizi/process/.venv/bin/python3.14 -m compileall -q lambda gcp-functions/queries-gcp tests
/Users/whizi/process/.venv/bin/python3.14 tests/smoke_d_group.py
/Users/whizi/process/.venv/bin/python3.14 -m unittest tests/test_d_group_handlers.py
```
