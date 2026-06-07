#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AWS_REGION="${AWS_REGION:-us-east-1}"
DDB_STACK_NAME="${DDB_STACK_NAME:-aussie-ecolens-dynamodb}"
SNS_STACK_NAME="${SNS_STACK_NAME:-aussie-ecolens-sns}"

aws cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${DDB_STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/dynamodb/template.yaml"

aws cloudformation deploy \
  --region "${AWS_REGION}" \
  --stack-name "${SNS_STACK_NAME}" \
  --template-file "${ROOT_DIR}/infra/sns/template.yaml"

echo "DynamoDB outputs:"
aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${DDB_STACK_NAME}" \
  --query "Stacks[0].Outputs" \
  --output table

echo "SNS outputs:"
aws cloudformation describe-stacks \
  --region "${AWS_REGION}" \
  --stack-name "${SNS_STACK_NAME}" \
  --query "Stacks[0].Outputs" \
  --output table

