#!/usr/bin/env bash
# Deploy (or update) the stack and upload the Lambda code.
# Run from the project folder in AWS CloudShell:
#   API_TOKEN='choose-a-long-secret' bash scripts/deploy.sh
set -euo pipefail

STACK=${STACK:-enrollment-api}
PROJECT=${PROJECT:-enrollment-api}
REGION=${AWS_REGION:-$(aws configure get region || echo eu-north-1)}
: "${API_TOKEN:?Set API_TOKEN to a secret of 16+ characters}"
cd "$(dirname "$0")/.."

echo "==> Deploying stack '$STACK' in $REGION"
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file template.yaml \
  --parameter-overrides ProjectName="$PROJECT" ApiToken="$API_TOKEN" \
  --capabilities CAPABILITY_NAMED_IAM --no-fail-on-empty-changeset

echo "==> Uploading Lambda code"
BUILD=$(mktemp -d)
cp src/app.py "$BUILD/"
(cd "$BUILD" && zip -q function.zip app.py)
aws lambda update-function-code --region "$REGION" --function-name "$PROJECT" \
  --zip-file "fileb://$BUILD/function.zip" >/dev/null
aws lambda wait function-updated --region "$REGION" --function-name "$PROJECT"
rm -rf "$BUILD"

URL=$(aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" --output text)
echo
echo "API is live: $URL"
echo "Test it:     python3 scripts/smoke_test.py $URL \"\$API_TOKEN\""
