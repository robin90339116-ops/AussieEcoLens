#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/gcp-functions/queries-gcp"

GCP_REGION="${GCP_REGION:-australia-southeast1}"
GCP_PROJECT="${GCP_PROJECT:-}"
AWS_REGION="${AWS_REGION:-us-east-1}"
FILES_TABLE="${FILES_TABLE:-AussieEcoLensFiles}"
COGNITO_REGION="${COGNITO_REGION:-us-east-1}"
COGNITO_USER_POOL_ID="${COGNITO_USER_POOL_ID:-us-east-1_lb6SisPnD}"
COGNITO_APP_CLIENT_ID="${COGNITO_APP_CLIENT_ID:-fvmq1uralbq80r9q7nrnonh73}"
CORS_ALLOW_ORIGIN="${CORS_ALLOW_ORIGIN:-http://localhost:3000}"
PRESIGNED_URL_EXPIRES_SECONDS="${PRESIGNED_URL_EXPIRES_SECONDS:-900}"

if ! command -v gcloud >/dev/null 2>&1; then
  echo "gcloud CLI is required. Install and log in before running this script." >&2
  exit 1
fi

if [[ -z "${GCP_PROJECT}" ]]; then
  GCP_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
fi

if [[ -z "${GCP_PROJECT}" || "${GCP_PROJECT}" == "(unset)" ]]; then
  echo "Set GCP_PROJECT or run: gcloud config set project <project-id>" >&2
  exit 1
fi

for required in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN; do
  if [[ -z "${!required:-}" ]]; then
    echo "Missing ${required}. Refresh AWS Academy credentials and export it before deploying." >&2
    exit 1
  fi
done

ENV_VARS="AWS_REGION=${AWS_REGION},FILES_TABLE=${FILES_TABLE},COGNITO_REGION=${COGNITO_REGION},COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID},COGNITO_APP_CLIENT_ID=${COGNITO_APP_CLIENT_ID},AUTH_REQUIRED=true,CORS_ALLOW_ORIGIN=${CORS_ALLOW_ORIGIN},PRESIGN_MEDIA_URLS=true,PRESIGNED_URL_EXPIRES_SECONDS=${PRESIGNED_URL_EXPIRES_SECONDS},AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID},AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY},AWS_SESSION_TOKEN=${AWS_SESSION_TOKEN}"

gcloud functions deploy q1_query_by_tags \
  --gen2 \
  --project="${GCP_PROJECT}" \
  --runtime=python312 \
  --region="${GCP_REGION}" \
  --source="${SOURCE_DIR}" \
  --entry-point=q1_query_by_tags \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="${ENV_VARS}"

gcloud functions deploy q2_query_by_species \
  --gen2 \
  --project="${GCP_PROJECT}" \
  --runtime=python312 \
  --region="${GCP_REGION}" \
  --source="${SOURCE_DIR}" \
  --entry-point=q2_query_by_species \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="${ENV_VARS}"

Q1_URL="$(gcloud functions describe q1_query_by_tags --gen2 --project="${GCP_PROJECT}" --region="${GCP_REGION}" --format='value(serviceConfig.uri)')"
Q2_URL="$(gcloud functions describe q2_query_by_species --gen2 --project="${GCP_PROJECT}" --region="${GCP_REGION}" --format='value(serviceConfig.uri)')"

cat <<EOF
GCP Q1/Q2 deployed.

Q1_URL=${Q1_URL}
Q2_URL=${Q2_URL}

Give these URLs to C if the frontend calls GCP directly.
EOF

