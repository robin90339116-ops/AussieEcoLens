# Shared D group helper package

`aussie_ecolens_db.py` is the shared helper library for A, B, and D.

Functions for A and B:

- `write_record(...)`: B calls this after ML tagging to write a file record.
- `get_by_checksum(checksum)`: A calls this from dedup Lambda.
- `publish_new_file_notification(...)`: B calls this after `write_record` if SNS notifications are enabled.

Functions for D APIs:

- `get_by_url(url)`
- `get_by_thumbnail_url(thumbnail_url)`
- `query_by_tag_counts(required_tags, owner_id=None, limit=100)`
- `query_by_species(species, owner_id=None, limit=100)`
- `update_tags(urls, tags, operation)`
- `delete_record(file_id=None, url=None)`
- `list_subscriptions(user_email=None)`
- `attach_presigned_media_urls(item)`
- `attach_presigned_media_urls_to_items(items)`

`query_by_tag_counts` and `query_by_species` automatically add short-lived
`original_access_url` and `thumbnail_access_url` fields when the record points
to private S3 media. They also keep `original_raw_url` and `thumbnail_raw_url`
when signing succeeds.

If upload metadata does not yet include the real owner, set
`DEFAULT_OWNER_ID=unknown-owner` or another team-agreed placeholder before B
writes records. Replace it with the Cognito owner once A/B pass that value.

Packaging options:

1. Run `scripts/package_d_lambdas.sh` to copy this directory into each Lambda package.
2. Or publish it as a Lambda layer under `/opt/python`.

Required Python dependency: `boto3`.
