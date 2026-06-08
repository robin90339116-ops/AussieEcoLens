# Aussie EcoLens B Module

This folder contains the Lambda + ML implementation for FIT5225 Assignment 2.

## Responsibilities

- Generate compressed image thumbnails after upload.
- Run MegaDetector and the fine-tuned SpeciesNet model to identify wildlife species.
- Return metadata containing file type, original URL, thumbnail URL, tag counts, and predictions.
- Package the ML inference code as an AWS Lambda container image for deployment through ECR.

## Deployment routes

There are two supported deployment routes for the ML compute. Both reuse the same
`ecolens_core.py` inference code.

- Route A (AWS): run the ML and thumbnail logic as AWS Lambda functions (the ML one as a
  container image via ECR). See `DEPLOYMENT.md`.
- Route B (Oracle/OCI): run the heavy ML inference as a FastAPI service on an Oracle Cloud
  instance, kept serverless-triggered by a lightweight AWS Lambda. See `ORACLE_DEPLOYMENT.md`.
  This is the recommended route given AWS Academy limits and the large model container.

## Important Files

- `ecolens_core.py`: shared thumbnail, video frame extraction, detection, classification, and metadata helpers.
- `thumbnail_lambda.py`: AWS Lambda handler for thumbnail generation (Route A).
- `ml_lambda.py`: AWS Lambda container handler for ML tagging (Route A).
- `Dockerfile.ml`: Docker build file for the ML Lambda image (Route A).
- `ml_service.py`: FastAPI ML inference service for Oracle/OCI (Route B).
- `s3_trigger_lambda.py`: lightweight AWS Lambda that forwards S3 events to the OCI service (Route B).
- `Dockerfile.service` / `docker-compose.yml` / `aussie-ecolens-ml.service`: OCI container + auto-start (Route B).
- `requirements-lambda.txt`: ML dependencies. `requirements-service.txt`: web service dependencies.
- `INTERFACE_CONTRACT.md`: input/output contract for A/C/D team integration.
- `DEPLOYMENT.md`: AWS Lambda, Docker, and ECR deployment guide (Route A).
- `ORACLE_DEPLOYMENT.md`: Oracle Cloud deployment guide and multi-cloud data flow (Route B).
- `local_test.py`: local thumbnail and metadata tests.
- `batch.py`: local batch runner using the refactored shared functions.

## Local Quick Test

Required Python version is 3.12.

Install lightweight local dependencies for thumbnail testing:

```bash
python -m pip install Pillow
```

Run a thumbnail test:

```bash
python local_test.py --mode thumbnail --image ../test_images/Alectura_lathami_1.JPG
```

Run a metadata contract sample:

```bash
python local_test.py --mode metadata-sample --image ../test_images/Alectura_lathami_1.JPG
```

## Full ML Inference (Verified)

The MegaDetector + SpeciesNet pipeline has been run and verified locally on CPU.
Set up a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install torch==2.12.0 torchvision==0.27.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lambda.txt
# megadetector pulls in opencv-python (needs libGL); replace it with the headless build:
pip uninstall -y opencv-python
pip install --force-reinstall --no-deps opencv-python-headless==4.13.0.92
```

Run full inference on a single image:

```bash
python local_test.py --mode ml --image ../test_images/Alectura_lathami_1.JPG
```

Verified results across 8 test species are recorded in
`test_results/REAL_INFERENCE_RESULTS.md` and `test_results/real_ml_inference.json`.
All species were identified correctly (7 at 100% confidence, 1 at 99.2%), and
`Bos_taurus_1.JPG` returned a count of 6 cattle, confirming multi-instance tag counting.

### Important dependency notes

- `onnx2torch` is required at runtime because `model.pt` (SpeciesNet) was exported via
  onnx2torch and references its classes during unpickling.
- Use `opencv-python-headless`, not `opencv-python`, to avoid the `libGL.so.1` error in Lambda.
- The MegaDetector detector and SpeciesNet model are cached in `model_cache` so warm Lambda
  invocations skip model reloading (first image ~20s cold, later images ~10s warm on CPU).

For deployment, follow `DEPLOYMENT.md`.
