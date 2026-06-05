# DynamoDB schema

## `AussieEcoLensFiles`

Primary key: `file_id` string.

Attributes:

- `checksum`: SHA-256 checksum for duplicate detection.
- `type`: `image` or `video`.
- `original_url`: S3 URL or signed/public URL for the original media.
- `thumbnail_url`: S3 URL or signed/public URL for the thumbnail.
- `tags`: map of species name to count, for example `{ "wombat": 2, "magpie": 1 }`.
- `owner_id`: Cognito user `sub` or email.
- `upload_time`: UTC ISO timestamp.
- `last_modified`: UTC ISO timestamp.
- `original_s3_key`: optional S3 key used by Q6 deletion.
- `thumbnail_s3_key`: optional S3 key used by Q6 deletion.

Indexes:

- `checksum-index`: partition key `checksum`, used by A's dedup Lambda.
- `owner_id-index`: partition key `owner_id`, used to list a user's files.

## `AussieEcoLensNotificationsSub`

Primary key: `user_email` string.

Attributes:

- `species_list`: subscribed species names.
- `created_at`: UTC ISO timestamp.

