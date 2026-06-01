# B Module Deployment Guide

This guide covers the Lambda + ML module for FIT5225 Assignment 2.

## Components

- `thumbnail_lambda.py`: standard Python Lambda handler for generating compressed image thumbnails.
- `ml_lambda.py`: Lambda container handler for MegaDetector + SpeciesNet tagging.
- `Dockerfile.ml`: container image definition for the ML Lambda.
- `ecolens_core.py`: shared image/video/ML helper functions.

## Thumbnail Lambda

Use a normal Python 3.12 Lambda package or layer containing:

- `thumbnail_lambda.py`
- `ecolens_core.py`
- `Pillow`
- `boto3` (already available in AWS Lambda runtime, but include if packaging manually)

Suggested environment variables:

```text
THUMBNAIL_PREFIX=thumbnails/
THUMBNAIL_BUCKET=<same-as-upload-bucket-or-dedicated-thumbnail-bucket>
MAX_THUMBNAIL_DIMENSION=320
JPEG_QUALITY=82
```

Trigger:

```text
S3 ObjectCreated on uploads/ prefix
```

Suggested runtime settings:

```text
Memory: 512 MB
Timeout: 30 seconds
```

## ML Lambda Container

The ML model files are large, so use a Lambda container image rather than a zip package.

Build locally:

```bash
cd /home/ubuntu/fit5225/ass2/AussieEcoLense
docker build -f Dockerfile.ml -t aussie-ecolens-ml:latest .
```

Create an ECR repository:

```bash
aws ecr create-repository --repository-name aussie-ecolens-ml
```

Authenticate Docker to ECR:

```bash
aws ecr get-login-password --region <region> \
  | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
```

Tag and push:

```bash
docker tag aussie-ecolens-ml:latest <account-id>.dkr.ecr.<region>.amazonaws.com/aussie-ecolens-ml:latest
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/aussie-ecolens-ml:latest
```

Create or update the Lambda function using the pushed image URI. Suggested runtime settings:

```text
Memory: 4096 MB or higher
Timeout: 300-900 seconds for demo stability
Ephemeral storage: 2048 MB or higher
Architecture: x86_64
```

Suggested environment variables:

```text
MD_MODEL_PATH=/var/task/mdv5a.pt
SPECIES_MODEL_PATH=/var/task/model.pt
LABELS_PATH=/var/task/labels.txt
THUMBNAIL_PREFIX=thumbnails/
THUMBNAIL_BUCKET=<thumbnail-bucket>
DYNAMODB_TABLE=<optional-dynamodb-table-from-D-module>
METADATA_API_URL=<optional-D-module-api-endpoint>
```

If both `DYNAMODB_TABLE` and `METADATA_API_URL` are unset, the ML Lambda will return metadata
without persisting it. This is useful for isolated B module testing.

### Verified dependency requirements

These were confirmed by running the full pipeline locally on CPU:

- `onnx2torch==1.5.15` and `onnx==1.21.0` are mandatory. `model.pt` (SpeciesNet) was exported
  through onnx2torch, so unpickling fails with `ModuleNotFoundError: onnx2torch` if it is missing.
- Use `opencv-python-headless`, never `opencv-python`. The non-headless build needs `libGL.so.1`,
  which is not present in the Lambda runtime. `Dockerfile.ml` removes opencv-python and force
  installs the headless build.
- Install CPU-only `torch`/`torchvision` from `https://download.pytorch.org/whl/cpu` to keep the
  image small (the default PyPI wheels bundle CUDA).
- The protobuf resolver warning from `ultralytics-yolov5` is benign; runtime works with the
  protobuf version required by onnx.

### Performance notes (CPU, verified)

- Cold start: first image takes roughly 20 seconds, including a one-time MegaDetector load (~5-6s)
  and SpeciesNet load (~2s).
- Warm path: subsequent images take roughly 10 seconds because the detector and model are cached
  in `model_cache`.
- Recommend at least 4096 MB memory and a 300s+ timeout for demo stability, and use provisioned
  concurrency or a keep-warm ping if smoother demo latency is needed.

## IAM Permissions Needed

Thumbnail Lambda:

- `s3:GetObject` on upload bucket
- `s3:PutObject` on thumbnail prefix/bucket

ML Lambda:

- `s3:GetObject` on upload bucket
- `dynamodb:PutItem` if writing directly to DynamoDB
- network access to `METADATA_API_URL` if using the D module API

## Example Test Event

```json
{
  "bucket": "aussie-ecolens-uploads",
  "key": "uploads/Alectura_lathami_1.JPG",
  "checksum": "optional-sha256",
  "thumbnail_url": "https://aussie-ecolens-uploads.s3.amazonaws.com/thumbnails/Alectura_lathami_1.jpg"
}
```

## Demo Notes

For a smooth demo, prepare three known images from `test_images`:

- `Alectura_lathami_1.JPG`
- `Felis_catus_1.JPG`
- `Sus_scrofa_1.JPG`

The expected demo flow is:

```text
Upload image -> S3 trigger -> thumbnail Lambda -> ML Lambda -> metadata JSON -> DB/query UI
```
