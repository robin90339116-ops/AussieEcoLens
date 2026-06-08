# B Module Demo Checklist

Use this checklist to demonstrate ZHU WENXUAN's Lambda + ML contribution.

## Before Demo

- Confirm the upload bucket has the S3 `ObjectCreated` trigger for `thumbnail_lambda.py`.
- Confirm the ML Lambda container image has been deployed from ECR.
- Confirm `THUMBNAIL_PREFIX`, `THUMBNAIL_BUCKET`, and optional `DYNAMODB_TABLE` or
  `METADATA_API_URL` environment variables are configured.
- Confirm D module can store the JSON fields from `metadata_schema.json`.
- Confirm C module displays `thumbnail_url`, `original_url`, and `tags`.

## Suggested Images

Use images from `../test_images`:

- `Alectura_lathami_1.JPG`
- `Felis_catus_1.JPG`
- `Sus_scrofa_1.JPG`

## Demo Flow

1. Upload a test image through the application or presigned URL flow.
2. Show that the thumbnail Lambda creates a compressed image under the `thumbnails/` prefix.
3. Show that the ML Lambda returns a metadata payload containing `file_type`, `original_url`,
   `thumbnail_url`, `tags`, `predictions`, and `created_at`.
4. Show that the D module stores the metadata in the database.
5. Use the UI or query API to retrieve the uploaded image by species tag.
6. Click or open the thumbnail result to verify it maps back to the original full-size image.

## Local Evidence Already Generated

`test_results/demo_evidence.json` records local thumbnail tests for three images:

- `Alectura_lathami_1.JPG`: thumbnail generated at 320x240, around 5.57% of original size.
- `Felis_catus_1.JPG`: thumbnail generated at 320x180, around 0.52% of original size.
- `Sus_scrofa_1.JPG`: thumbnail generated at 320x240, around 4.19% of original size.

`test_results/REAL_INFERENCE_RESULTS.md` and `test_results/real_ml_inference.json` record the
full MegaDetector + SpeciesNet pipeline run on CPU across 8 species. All were classified
correctly (7 at 100%, 1 at 99.2%), and `Bos_taurus_1.JPG` returned a count of 6 cattle,
demonstrating multi-instance tag counting.

This means the ML module is fully working locally; the same container can be deployed to ECR and
attached to Lambda with team AWS credentials for the cloud demo.
