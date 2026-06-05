# SNS notification Lambda

This handler supports:

- `subscribe`: subscribe a user email to one or more species.
- `unsubscribe`: remove a local subscription and optionally unsubscribe an SNS ARN.
- `publish`: helper endpoint for B's ML Lambda after it writes a new file record.

Required environment variables:

- `SNS_TOPIC_ARN`
- `NOTIFICATIONS_TABLE`, default `AussieEcoLensNotificationsSub`
- `AWS_REGION`, default `ap-southeast-2`
- `CORS_ALLOW_ORIGIN`, default `*`

