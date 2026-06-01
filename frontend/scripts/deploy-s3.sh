#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${VITE_DEPLOY_BUCKET:-}" ]]; then
  echo "VITE_DEPLOY_BUCKET is required, for example: aussie-ecolens-frontend" >&2
  exit 1
fi

npm run build
aws s3 sync dist/ "s3://${VITE_DEPLOY_BUCKET}" --delete

if [[ -n "${VITE_CLOUDFRONT_DISTRIBUTION_ID:-}" ]]; then
  aws cloudfront create-invalidation \
    --distribution-id "${VITE_CLOUDFRONT_DISTRIBUTION_ID}" \
    --paths "/*"
fi

