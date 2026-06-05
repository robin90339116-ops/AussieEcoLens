# AWS query Lambdas

These handlers cover D group's AWS-side query and management APIs:

- `q3_thumbnail_lookup`: thumbnail URL to original media URL lookup.
- `q4_image_search`: pass a query image to B's ML Lambda, then query by returned tags without storing the query image.
- `q5_update_tags`: batch add/remove tags.
- `q6_delete_file`: delete original object, thumbnail object, and DynamoDB record.

Package each function with `Project/lambda/shared` on the Python path or publish
`lambda/shared` as a Lambda layer under `/opt/python`.

Required environment variables:

- `FILES_TABLE`, default `AussieEcoLensFiles`
- `AWS_REGION`, default `ap-southeast-2`
- `ORIGINAL_BUCKET`, required only when records store `original_s3_key`
- `THUMBNAIL_BUCKET`, required only when records store `thumbnail_s3_key`
- `ML_QUERY_LAMBDA_NAME`, required only for Q4
- `CORS_ALLOW_ORIGIN`, default `*`
