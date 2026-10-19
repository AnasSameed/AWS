#!/usr/bin/env bash
# Delete everything this project created (table, function, role, API, logs).
set -euo pipefail
STACK=${STACK:-enrollment-api}
REGION=${AWS_REGION:-$(aws configure get region || echo eu-north-1)}
aws cloudformation delete-stack --region "$REGION" --stack-name "$STACK"
aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "$STACK"
echo "Stack $STACK deleted. Nothing from this project is left running."
