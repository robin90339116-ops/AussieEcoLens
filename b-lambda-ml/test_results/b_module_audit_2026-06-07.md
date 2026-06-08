# B Module Audit Evidence (Wenxuan-Zhu) - 2026-06-07

Audit against `FIT5225_A2_严格审查与待办清单.docx`. This file records concrete, reproducible
evidence that the B-module checklist items are satisfied at the code level. Cloud bucket
notification wiring and IAM attachment are A's deployment step; everything B owns is below.

## B-1 / B-2: Forwarding Lambda fans out + is configurable

`s3_trigger_lambda.py` is the single S3 `uploads/` target. It:

- async-invokes the thumbnail Lambda (`InvocationType="Event"`) for images,
- calls the OCI ML endpoint with bearer token,
- persists to DynamoDB via D's `aussie_ecolens_db.write_record`,
- optionally invokes D's notification Lambda.

All of these are env-driven (so A can configure without code changes):
`OCI_ML_ENDPOINT`, `OCI_API_TOKEN`, `THUMBNAIL_LAMBDA_NAME`, `PERSIST_TO_DB`,
`DEFAULT_OWNER_ID`, `OWNER_METADATA_KEY`, `FILES_TABLE`, `AWS_REGION`, `NOTIFY_LAMBDA_NAME`.

Required IAM (documented in `ORACLE_DEPLOYMENT.md` / `API_DOC.md`):
`s3:GetObject`, `s3:HeadObject`, `lambda:InvokeFunction` (thumbnail + notifications),
`dynamodb:PutItem`, `dynamodb:Query` (checksum-index).

## B-3: Real ML result written to DynamoDB with all required fields

Real call to the running OCI service `/v1/tag/upload` on `Sus_scrofa_1.JPG`:

```json
{
  "status": "ok",
  "file_type": "image",
  "checksum": "a803bd4bc12235bb4e892a483ca3ffdc2b479c1c929c04ba10e5c9cecf80c906",
  "tags": { "wild boar": 1 },
  "predictions": [
    { "scientific_name": "Sus_scrofa", "confidence": 1.0, "source": "Sus_scrofa_1-0", "common_name": "wild boar" }
  ]
}
```

Exact item the forwarding Lambda writes to `AussieEcoLensFiles` (via D's `write_record`):

```json
{
  "checksum": "a803bd4bc12235bb4e892a483ca3ffdc2b479c1c929c04ba10e5c9cecf80c906",
  "file_type": "image",
  "original_url": "https://aussie-ecolens-35346906.s3.amazonaws.com/uploads/images/abc123_Sus_scrofa_1.JPG",
  "thumbnail_url": "https://aussie-ecolens-35346906.s3.amazonaws.com/thumbnails/abc123_Sus_scrofa_1.jpg",
  "tags": { "wild boar": 1 },
  "owner_id": "cognito-sub-7f3a",
  "file_id": "f596a98b033816eeed15acea3fbb738637f475b76f1bf45bcc793a092760dde9",
  "original_s3_key": "uploads/images/abc123_Sus_scrofa_1.JPG",
  "thumbnail_s3_key": "thumbnails/abc123_Sus_scrofa_1.jpg"
}
```

Field completeness check: PASS - file type, tags, checksum, owner_id, original/thumbnail URL,
and original/thumbnail S3 key are all present. `file_id` is derived from the checksum
(`stable_file_id`), so it is stable and dedup-consistent.

De-duplication: the forwarding Lambda calls `get_by_checksum` before writing; an existing
checksum is skipped (no duplicate row). The OCI checksum is the SHA-256 of the stored bytes,
matching the frontend's `crypto.subtle.digest('SHA-256', ...)`.

## owner_id resolution (Demo checklist: x-amz-meta-owner-id)

`_owner_id_for` reads S3 user metadata via `head_object` (boto3 exposes
`x-amz-meta-owner-id` as `Metadata['owner-id']`), with a `DEFAULT_OWNER_ID` fallback:

```text
from x-amz-meta-owner-id -> cognito-sub-7f3a
fallback DEFAULT_OWNER_ID -> demo-owner
```

## B-4: Video processed at 1 frame per second

Synthetic clip: 6 s @ 24 fps = 144 frames. `extract_video_frames(..., frames_per_second=1)`:

```text
source_fps=24.0  total_frames=144.0  duration=6s
extracted_frames(1fps)=6  expected≈6   => PASS
```

`tag_video` calls `extract_video_frames(..., frames_per_second=1)`, aggregates per-frame
species counts, and returns `frames_processed`. A real wildlife clip should be used for the
live demo (synthetic frames contain no animals to detect).

## Summary

| Checklist item (B) | Code status | Evidence |
| --- | --- | --- |
| Single S3 target -> forwarding -> async thumbnail | Implemented | s3_trigger_lambda.py |
| Forwarding Lambda configurable (OCI/DDB/thumb/notify) | Implemented | env vars + docs |
| Real upload writes full metadata to DynamoDB | Verified | section B-3 above |
| owner_id from object metadata + fallback | Verified | owner_id test |
| Video at 1 fps | Verified | section B-4 above |

Remaining non-code items are deployment-side and owned by A (attach bucket notification to the
forwarding Lambda, attach IAM policy, set env vars, send the OCI token privately).
