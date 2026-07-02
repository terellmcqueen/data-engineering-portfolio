#!/bin/bash
# zip and deploy to Lambda
set -e

FUNCTION_NAME="redshift-query-sandbox"

echo "Packaging..."
zip -j function.zip lambda_function.py

echo "Deploying to $FUNCTION_NAME..."
aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file fileb://function.zip \
    --region us-east-1

rm function.zip
echo "Done."
