#!/bin/bash
set -e

# Default values
ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STACK_PREFIX="cloud-defender-${ENVIRONMENT}"
S3_BUCKET="${STACK_PREFIX}-cfn-${ACCOUNT_ID}"

echo "====================================================="
echo "DELETING Cloud Defender Game from ${ENVIRONMENT} environment in ${REGION} region"
echo "====================================================="
echo "WARNING: This will delete ALL resources associated with the Cloud Defender game."
echo "This includes ECS services, ECR repositories, DynamoDB tables, VPC, and all associated resources."
echo "====================================================="
read -p "Are you sure you want to proceed? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Cleanup cancelled."
    exit 1
fi

echo "Starting cleanup process..."

# Get ECS cluster name
echo "Retrieving ECS cluster name..."
ECS_CLUSTER=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-cluster" \
  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
  --output text \
  --region ${REGION} 2>/dev/null || echo "")

# Get ECR repository URI
echo "Retrieving ECR repository URI..."
ECR_REPOSITORY_URI=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-ecr" \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" \
  --output text \
  --region ${REGION} 2>/dev/null || echo "")

# Extract repository name from URI
if [ ! -z "$ECR_REPOSITORY_URI" ]; then
  ECR_REPOSITORY_NAME=$(echo $ECR_REPOSITORY_URI | cut -d'/' -f2)
fi

# 1. Delete the ECS service stack
echo "Deleting ECS service stack..."
aws cloudformation delete-stack --stack-name "${STACK_PREFIX}-service" --region ${REGION} || true
echo "Waiting for ECS service stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_PREFIX}-service" --region ${REGION} || true

# 2. Delete the ECS cluster stack
echo "Deleting ECS cluster stack..."
aws cloudformation delete-stack --stack-name "${STACK_PREFIX}-cluster" --region ${REGION} || true
echo "Waiting for ECS cluster stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_PREFIX}-cluster" --region ${REGION} || true

# 3. Delete the DynamoDB table stack
echo "Deleting DynamoDB table stack..."
aws cloudformation delete-stack --stack-name "${STACK_PREFIX}-db" --region ${REGION} || true
echo "Waiting for DynamoDB table stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_PREFIX}-db" --region ${REGION} || true

# 4. Delete the VPC stack
echo "Deleting VPC stack..."
aws cloudformation delete-stack --stack-name "${STACK_PREFIX}-vpc" --region ${REGION} || true
echo "Waiting for VPC stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_PREFIX}-vpc" --region ${REGION} || true

# 5. Delete all images from ECR repository
if [ ! -z "$ECR_REPOSITORY_NAME" ]; then
  echo "Deleting images from ECR repository ${ECR_REPOSITORY_NAME}..."
  # Get image digests
  IMAGE_DIGESTS=$(aws ecr list-images --repository-name ${ECR_REPOSITORY_NAME} --region ${REGION} --query 'imageIds[*].imageDigest' --output text 2>/dev/null || echo "")
  
  # Delete images if any exist
  if [ ! -z "$IMAGE_DIGESTS" ]; then
    for digest in $IMAGE_DIGESTS; do
      echo "Deleting image: $digest"
      aws ecr batch-delete-image --repository-name ${ECR_REPOSITORY_NAME} --image-ids imageDigest=$digest --region ${REGION} || true
    done
  fi
fi

# 6. Delete the ECR repository stack
echo "Deleting ECR repository stack..."
aws cloudformation delete-stack --stack-name "${STACK_PREFIX}-ecr" --region ${REGION} || true
echo "Waiting for ECR repository stack deletion to complete..."
aws cloudformation wait stack-delete-complete --stack-name "${STACK_PREFIX}-ecr" --region ${REGION} || true

# 7. Delete the S3 bucket with CloudFormation templates
if aws s3 ls "s3://${S3_BUCKET}" --region ${REGION} 2>&1 > /dev/null; then
  echo "Emptying and deleting S3 bucket ${S3_BUCKET}..."
  aws s3 rm "s3://${S3_BUCKET}" --recursive --region ${REGION} || true
  aws s3 rb "s3://${S3_BUCKET}" --force --region ${REGION} || true
fi

echo "====================================================="
echo "Cleanup complete!"
echo "====================================================="
echo "All Cloud Defender Game resources for environment '${ENVIRONMENT}' in region '${REGION}' have been deleted."
echo "====================================================="
