#!/usr/bin/env bash
set -euo pipefail

Q1_URL="${Q1_URL:-}"
Q2_URL="${Q2_URL:-}"
TOKEN="${TOKEN:-}"

if [[ -z "${Q1_URL}" || -z "${Q2_URL}" ]]; then
  echo "Set Q1_URL and Q2_URL before running this script." >&2
  exit 1
fi

if [[ -z "${TOKEN}" ]]; then
  echo "Set TOKEN to a valid Cognito JWT before running authenticated checks." >&2
  exit 1
fi

echo "Checking Q1 AND tag-count query"
curl -i -X POST "${Q1_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"tags":{"wombat":1},"limit":5}'

echo
echo "Checking Q2 species query"
curl -i -X POST "${Q2_URL}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"species":"wombat","limit":5}'

