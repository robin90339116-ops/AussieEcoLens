# D group demo checklist

Use this checklist after AWS/GCP accounts are available.

## Before frontend demo

- A confirms final API Gateway base URL.
- A confirms Cognito User Pool ID, App Client ID, issuer, and JWT audience.
- B confirms Oracle tagging upload URL and token for Q4.
- D confirms DynamoDB table name and indexes:
  - `AussieEcoLensFiles`
  - `checksum-index`
  - `owner_id-index`
  - `AussieEcoLensNotificationsSub`
- D confirms SNS topic ARN and email subscription behavior.
- If GCP reads DynamoDB with AWS Academy credentials, refresh the GCP AWS
  environment variables before the demo because session credentials expire.

## Endpoint routing

Preferred formal demo route:

| Query | Frontend calls | Backend target |
| --- | --- | --- |
| Q1 tag-count AND query | A API Gateway or protected GCP HTTPS | GCP `q1_query_by_tags` |
| Q2 species query | A API Gateway or protected GCP HTTPS | GCP `q2_query_by_species` |
| Q3 thumbnail reverse lookup | A API Gateway | AWS Lambda `q3_thumbnail_lookup` |
| Q4 query file search | A API Gateway `/query/by-file` | AWS Lambda `q4_image_search`, then B Oracle tagging endpoint |
| Q5 update tags | A API Gateway | AWS Lambda `q5_update_tags` |
| Q6 delete file | A API Gateway | AWS Lambda `q6_delete_file` |
| Notifications | A API Gateway | AWS Lambda `notifications` and SNS |

Q1/Q2 can be direct GCP HTTPS only when Cognito JWT verification is enabled.
B's Oracle token is never exposed to the frontend.

## Smoke-test sequence

1. Get a valid Cognito JWT from the frontend login flow.
2. Upload at least one tagged image through A/B flow so DynamoDB has a record.
3. Run Q1 with `{"wombat": 2, "magpie": 1}` and confirm AND logic.
4. Run Q2 with one known species and confirm file list.
5. Run Q3 with a known thumbnail URL and confirm original URL.
6. Run Q4 with a query image and confirm:
   - B Oracle tagging endpoint returns tags.
   - D returns matching records.
   - Query image is not stored in S3 or DynamoDB.
7. Run Q5 add/remove tags and confirm `last_modified` changes.
8. Run Q6 delete and confirm S3 original, S3 thumbnail, and DynamoDB record are removed.
9. Subscribe to one species and confirm SNS email confirmation is received.
10. Publish a notification event and confirm only matching subscriptions receive it.

## Known placeholders to replace

- `<A_API_GATEWAY_BASE_URL>`
- `<GCP_Q1_URL>`
- `<GCP_Q2_URL>`
- `<COGNITO_USER_POOL_ID>`
- `<COGNITO_APP_CLIENT_ID>`
- `<ORACLE_TAG_UPLOAD_URL>`
- `<ORACLE_API_TOKEN>`
- `<SNS_TOPIC_ARN>`
- `<AWS_ACCESS_KEY_ID>`
- `<AWS_SECRET_ACCESS_KEY>`
- `<AWS_SESSION_TOKEN>`
