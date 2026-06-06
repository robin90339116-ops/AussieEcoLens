# FIT5225-A2 AussieEcoLens

This branch contains D group's database, query API, GCP, and notification
handoff work.

## D group scope

- DynamoDB schema and helper library.
- AWS Lambda handlers for Q3, Q4, Q5, Q6, and notifications.
- GCP Cloud Functions for Q1 and Q2.
- Cognito JWT verification for direct GCP HTTPS access.
- SNS notification helper and subscription API.
- API Gateway route handoff for A group.
- Local smoke tests and handler unit tests.

## Important integration boundary

For the formal frontend demo:

- Frontend should call A's API Gateway whenever possible.
- D's AWS Lambda handlers must be attached behind A's API Gateway with Cognito
  Authorizer.
- B's Oracle tagging token must remain private behind backend services.
- D's GCP Q1/Q2 endpoints may be exposed directly only as HTTPS endpoints with
  Cognito JWT verification enabled.

## Key files

- `D_GROUP_HANDOFF.md`: short teammate handoff.
- `docs/db-and-queries.md`: API contract and curl examples.
- `docs/demo-checklist.md`: final demo verification checklist.
- `docs/architecture.md`: architecture diagram draft for the report.
- `infra/api-gateway/d-group-openapi-fragment.yaml`: A group route handoff.
- `infra/dynamodb/template.yaml`: DynamoDB CloudFormation template.
- `infra/sns/template.yaml`: SNS CloudFormation template.
- `lambda/shared/`: DB and SNS helper code.
- `lambda/queries-aws/`: AWS Lambda handlers.
- `gcp-functions/queries-gcp/`: GCP Q1/Q2 functions.
- `tests/`: local checks that do not require cloud accounts.

## Local checks

Use the project Python environment:

```bash
/Users/whizi/process/.venv/bin/python3.14 -m compileall -q lambda gcp-functions/queries-gcp tests
/Users/whizi/process/.venv/bin/python3.14 tests/smoke_d_group.py
/Users/whizi/process/.venv/bin/python3.14 -m unittest tests/test_d_group_handlers.py
```

## Not included

Real deployment still needs the team's AWS and GCP accounts, A's Cognito values,
B's Oracle tagging URL/token, and final endpoint URLs.
