# SNS notification Lambda

This handler supports:

- `subscribe`: subscribe a user email to one or more species.
- `unsubscribe`: remove a local subscription and optionally unsubscribe an SNS ARN.
- `list` or `GET`: return subscriptions for C's subscription page.
- `publish`: helper endpoint for B after it writes a new file record.

Required environment variables:

- `SNS_TOPIC_ARN`
- `NOTIFICATIONS_TABLE`, default `AussieEcoLensNotificationsSub`
- `AWS_REGION`, default `us-east-1`
- `CORS_ALLOW_ORIGIN`, default `*`
