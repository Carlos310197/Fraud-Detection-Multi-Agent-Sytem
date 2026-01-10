#!/bin/bash
# Script to securely store OpenAI API key in AWS Systems Manager Parameter Store

set -e

PARAMETER_NAME="/fraud-detection/openai-api-key"
REGION="${AWS_REGION:-us-east-1}"

echo "========================================="
echo "OpenAI API Key Setup for AWS Lambda"
echo "========================================="
echo ""
echo "This script will securely store your OpenAI API key in AWS Systems Manager Parameter Store."
echo "The key will be encrypted and only accessible by your Lambda function."
echo ""

# Check if parameter already exists
if aws ssm get-parameter --name "$PARAMETER_NAME" --region "$REGION" &>/dev/null; then
    echo "⚠️  Parameter already exists at: $PARAMETER_NAME"
    echo ""
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted. Using existing parameter."
        exit 0
    fi
fi

# Prompt for API key
echo "Please enter your OpenAI API key (starts with sk-):"
read -s OPENAI_API_KEY
echo ""

# Validate format
if [[ ! $OPENAI_API_KEY =~ ^sk- ]]; then
    echo "❌ Error: OpenAI API key should start with 'sk-'"
    exit 1
fi

# Store in Parameter Store with encryption
echo "Storing API key in Parameter Store..."
aws ssm put-parameter \
    --name "$PARAMETER_NAME" \
    --value "$OPENAI_API_KEY" \
    --type "SecureString" \
    --region "$REGION" \
    --overwrite \
    --description "OpenAI API key for fraud detection Lambda function" \
    > /dev/null

echo "✅ API key successfully stored at: $PARAMETER_NAME"
echo ""
echo "The key is encrypted using AWS KMS and can only be accessed by:"
echo "  - IAM users/roles with ssm:GetParameter permission"
echo "  - Your fraud-detection Lambda function"
echo ""
echo "Next steps:"
echo "  1. Run: sam build && sam deploy"
echo "  2. Test with: curl -X POST https://<your-api-url>/transactions/T-2001/analyze"
echo ""
