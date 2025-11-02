#!/bin/bash

# Ultra Calendar - AWS App Runner Deployment Script
# Usage: ./deploy.sh [AWS_ACCOUNT_ID] [AWS_REGION]

set -e

# Configuration
AWS_ACCOUNT_ID=${1:-"YOUR_AWS_ACCOUNT_ID"}
AWS_REGION=${2:-"us-east-1"}
ECR_REPO="ultra-calendar"
IMAGE_TAG="latest"

echo "🚀 Ultra Calendar Deployment"
echo "============================"
echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ Error: AWS CLI is not installed"
    echo "Install from: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed"
    echo "Install from: https://www.docker.com/get-started"
    exit 1
fi

# Validate AWS account ID
if [ "$AWS_ACCOUNT_ID" = "YOUR_AWS_ACCOUNT_ID" ]; then
    echo "❌ Error: Please provide your AWS Account ID"
    echo "Usage: ./deploy.sh <AWS_ACCOUNT_ID> [AWS_REGION]"
    exit 1
fi

echo "📦 Step 1: Building Docker image..."
docker build -t $ECR_REPO:$IMAGE_TAG .

echo ""
echo "🔐 Step 2: Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo ""
echo "📋 Step 3: Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names $ECR_REPO --region $AWS_REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION

echo ""
echo "🏷️  Step 4: Tagging image..."
docker tag $ECR_REPO:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

echo ""
echo "⬆️  Step 5: Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Go to AWS App Runner console: https://console.aws.amazon.com/apprunner/home?region=$AWS_REGION"
echo "2. Create or update service with image:"
echo "   $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:$IMAGE_TAG"
echo "3. Configure environment variables (see README.md)"
echo "4. Set up custom domain: ultra-calendar.com"
echo ""
