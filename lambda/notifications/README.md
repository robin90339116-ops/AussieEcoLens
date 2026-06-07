# SNS notification Lambda

This handler supports:

- `subscribe`: subscribe a user email to one or more species, saving the SNS `subscription_arn`.
- `unsubscribe`: update the SNS filter policy or call SNS `unsubscribe` when no subscribed species remain.
- `list` or `GET`: return subscriptions for C's subscription page.
- `publish`: helper endpoint for B after it writes a new file record.

Repeated subscribe requests for the same email/species are deduplicated. New
species for an existing confirmed subscription update the SNS filter policy
instead of creating another email subscription.

Required environment variables:

- `SNS_TOPIC_ARN`
- `NOTIFICATIONS_TABLE`, default `AussieEcoLensNotificationsSub`
- `AWS_REGION`, default `us-east-1`
- `CORS_ALLOW_ORIGIN`, default `http://localhost:3000` when configured for frontend demo

Frontend route through A API Gateway:

- `GET/POST /notifications/subscribe`
