# Route B: ML Inference on Oracle Cloud (OCI)

This is the deployment route where the heavy MegaDetector + SpeciesNet inference runs on
an Oracle Cloud compute instance instead of AWS Lambda. It was chosen because the ML
container is large (PyTorch + two model files) and AWS Academy imposes IAM/role and
container limitations that make a heavy Lambda risky.

## Why this is allowed

The assignment only mandates **AWS Cognito** for authentication. All other services may be
hosted on a secondary cloud (GCP/Azure/Oracle). The "upload triggers a serverless function"
requirement is still satisfied because a lightweight AWS Lambda (`s3_trigger_lambda.py`) is
triggered by the S3 ObjectCreated event; it then forwards the work to the OCI service.

## Multi-cloud data flow

```mermaid
flowchart LR
    user["User / React UI"] -->|"Cognito auth"| cognito["AWS Cognito"]
    user -->|"presigned upload (x-amz-meta-owner-id)"| s3["AWS S3 Upload Bucket"]
    s3 -->|"ObjectCreated event (single target)"| trigger["AWS Lambda (s3_trigger_lambda)"]
    trigger -->|"async invoke (Event)"| thumb["AWS Lambda (thumbnail_lambda)"]
    thumb -->|"PUT thumbnail"| s3
    trigger -->|"presigned GET URL + bearer token (HTTPS)"| oci["OCI ML Service (FastAPI + PyTorch)"]
    oci -->|"download image via presigned URL"| s3
    oci -->|"metadata JSON (incl. SHA-256 checksum)"| trigger
    trigger -->|"write_record()"| ddb["DynamoDB AussieEcoLensFiles"]
    trigger -.->|"optional publish (tags)"| notify["D notifications Lambda -> SNS"]
    ddb --> results["D query API -> UI"]
```

- AWS: Cognito (auth), S3 (storage), API Gateway, the forwarding trigger Lambda, the
  thumbnail Lambda, DynamoDB, and D's notification/query Lambdas.
- Oracle (this instance): heavy ML inference service.
- GCP: D's query/notification functions can also run here against the same DynamoDB.

### Why the trigger Lambda fans out (S3 single-target limitation)

S3 allows only **one** notification target per bucket/event/prefix. So the thumbnail
Lambda and the ML forwarding Lambda cannot both be attached directly to `uploads/`.
The "doorbell" on `uploads/` is therefore the forwarding Lambda only; it asynchronously
invokes the thumbnail Lambda (`InvocationType="Event"`) and then calls the OCI service.

### Why the trigger Lambda writes to DynamoDB

The S3-triggered invocation is asynchronous: nothing consumes its return value, so ML
results were previously lost and the database stayed empty. The forwarding Lambda now
persists the OCI metadata with D's shared `aussie_ecolens_db.write_record` immediately
after a successful inference. The thumbnail URL is deterministic
(`thumbnails/<stem>.jpg`), so the record is complete even though the thumbnail is
generated asynchronously.

## Components

- `ml_service.py`: FastAPI service running on OCI. Loads models once at startup and reuses them.
- `Dockerfile.service`: container image for the OCI service.
- `docker-compose.yml`: run the service with restart policy and health check.
- `aussie-ecolens-ml.service`: systemd unit for auto-start on the OCI VM.
- `s3_trigger_lambda.py`: the small AWS Lambda triggered by S3 that calls this service.

## Security / cross-cloud token passing

All `/v1/*` routes require `Authorization: Bearer <token>`. The token is configured via
`API_AUTH_TOKEN` on the OCI service and `OCI_API_TOKEN` on the AWS trigger Lambda.

For the assignment's "securely pass AWS Cognito tokens to the secondary cloud" requirement,
two options:

1. Shared secret (implemented): the AWS side holds a secret and sends it as the bearer token.
   Simple and reliable for the demo.
2. Cognito JWT pass-through (upgrade path): the trigger Lambda forwards the caller's Cognito
   JWT, and `require_token` in `ml_service.py` is extended to validate the JWT signature
   against the Cognito JWKS endpoint. The validation hook is isolated in `require_token` so
   this change is localised.

Always run the OCI service behind HTTPS (OCI load balancer or a reverse proxy such as Caddy or
nginx with TLS), and restrict the security list / firewall so only the AWS trigger can reach it.

## Run on the OCI instance (Docker)

```bash
cd /home/ubuntu/fit5225/ass2/AussieEcoLense
echo "API_AUTH_TOKEN=$(openssl rand -hex 24)" > .env
# Optional: forward results straight to the D module DB API.
# echo "METADATA_API_URL=https://<d-module-endpoint>/records" >> .env
docker compose up -d --build
curl -s http://localhost:8080/health
```

Enable auto-start on boot:

```bash
sudo cp aussie-ecolens-ml.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now aussie-ecolens-ml.service
```

## Run without Docker (venv, used for local verification)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install torch==2.12.0 torchvision==0.27.0 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-lambda.txt
pip uninstall -y opencv-python && pip install --force-reinstall --no-deps opencv-python-headless==4.13.0.92
pip install -r requirements-service.txt
API_AUTH_TOKEN=test-token-123 uvicorn ml_service:app --host 0.0.0.0 --port 8080
```

## OCI networking checklist

- Open ingress on the chosen port (e.g. 8080 or 443) in the OCI security list / NSG.
- Open the same port in the instance OS firewall (e.g. `sudo iptables`/`firewalld`/ufw).
- Prefer placing the service behind an OCI Load Balancer with TLS, exposing only 443.
- Lock the source to the AWS Lambda egress (NAT gateway IP) where possible.

## AWS trigger / forwarding Lambda configuration

Environment variables:

```text
OCI_ML_ENDPOINT=https://<oci-host>:8080/v1/tag/s3
OCI_API_TOKEN=<same value as API_AUTH_TOKEN on OCI>   # send this to A privately
PRESIGN_EXPIRY=600
REQUEST_TIMEOUT=300

# Fan-out: async thumbnail generation (S3 single-target workaround)
THUMBNAIL_LAMBDA_NAME=aussie-ecolens-thumbnail        # name/ARN of thumbnail Lambda
THUMBNAIL_PREFIX=thumbnails/

# Persistence to DynamoDB (uses D's shared module)
PERSIST_TO_DB=true
DEFAULT_OWNER_ID=demo-owner                            # fallback when object has no owner
OWNER_METADATA_KEY=owner-id                            # S3 user-metadata key A sets on upload
FILES_TABLE=AussieEcoLensFiles                         # read by aussie_ecolens_db
AWS_REGION=us-east-1                                    # MUST match the team's region

# Optional: trigger D's tag-based notification (no DynamoDB Stream exists)
NOTIFY_LAMBDA_NAME=aussie-ecolens-notifications
```

Packaging: the deployment zip must include D's `lambda/shared/aussie_ecolens_db.py`
(and boto3) so `write_record` / `get_by_checksum` are importable. Example:

```bash
mkdir -p build && cp s3_trigger_lambda.py build/
cp ../path-to-D/lambda/shared/aussie_ecolens_db.py build/
cd build && zip -r ../trigger.zip . && cd ..
```

IAM permissions for this Lambda:

- `s3:GetObject`, `s3:HeadObject` on the upload bucket (presigned URLs + owner metadata).
- `lambda:InvokeFunction` on the thumbnail Lambda (and notifications Lambda if used).
- `dynamodb:PutItem` and `dynamodb:Query` (checksum-index) on `AussieEcoLensFiles`.
- Outbound network access to the OCI endpoint.

This Lambda is still tiny (boto3 + stdlib + D's db helper), so a normal zip package works
and avoids the AWS Academy container limitations entirely.

## Cross-team coordination notes (B module)

These were raised in the team tech-coordination doc and are addressed here:

1. **owner_id** is not in the S3 event. Convention agreed with D: A attaches the Cognito
   `sub` as S3 user metadata `x-amz-meta-owner-id` on the presigned PUT; B reads it via
   `head_object` and falls back to `DEFAULT_OWNER_ID`. D's `write_record` applies its own
   `DEFAULT_OWNER_ID` fallback as a final safety net.
2. **One S3 notification target**: configure the bucket `uploads/` event to invoke ONLY the
   forwarding Lambda. It fans out to the thumbnail Lambda. A configures the bucket once this
   is agreed.
3. **OCI token**: send `API_AUTH_TOKEN` (= `OCI_API_TOKEN`) to A privately so A can set it on
   the forwarding Lambda. Never commit it; never expose it to the frontend.
4. **Dedup checksum**: the OCI service now returns the SHA-256 of the stored bytes, matching
   the frontend's `crypto.subtle.digest('SHA-256', ...)`. The forwarding Lambda calls
   `get_by_checksum` before writing to avoid duplicate rows.

## Verified locally on this OCI instance

See `test_results/route_b_service_test.md`:

- `/health` returns `models_loaded: true`.
- Auth: no token -> 401, bad token -> 403, valid token -> 200.
- `/v1/tag/s3` (presigned-URL flow) returns full metadata, e.g. `Alectura_lathami_1.JPG` ->
  `{ "australian brushturkey": 1 }` at 99.99% confidence.
- `/v1/tag/upload` (query-by-file) returns tags without persisting the file.
