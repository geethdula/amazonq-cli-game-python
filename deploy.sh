#!/bin/bash
set -e

# Default values
ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}
FORCE_DEPLOY=${3:-false}
TIMESTAMP=$(date +%Y%m%d%H%M%S)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STACK_PREFIX="cloud-defender-${ENVIRONMENT}"
S3_BUCKET="${STACK_PREFIX}-cfn-${ACCOUNT_ID}"
ECR_REPOSITORY_NAME="${STACK_PREFIX}"
IMAGE_TAG="latest-${TIMESTAMP}"

echo "====================================================="
echo "Deploying Cloud Defender Game to ${ENVIRONMENT} environment in ${REGION} region"
echo "====================================================="

# Create S3 bucket for CloudFormation templates if it doesn't exist
if ! aws s3 ls "s3://${S3_BUCKET}" --region ${REGION} 2>&1 > /dev/null; then
  echo "Creating S3 bucket for CloudFormation templates..."
  aws s3 mb "s3://${S3_BUCKET}" --region ${REGION}
  aws s3api put-bucket-encryption \
    --bucket ${S3_BUCKET} \
    --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}' \
    --region ${REGION}
fi

# Upload CloudFormation templates to S3
echo "Uploading CloudFormation templates to S3..."
aws s3 sync ./cloudformation/ "s3://${S3_BUCKET}/templates/" --region ${REGION}

# Deploy ECR repository
echo "Deploying ECR repository..."
aws cloudformation deploy \
  --template-file ./cloudformation/ecr.yaml \
  --stack-name "${STACK_PREFIX}-ecr" \
  --parameter-overrides \
    Environment=${ENVIRONMENT} \
    RepositoryName=${ECR_REPOSITORY_NAME} \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Get ECR repository URI
ECR_REPOSITORY_URI=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-ecr" \
  --query "Stacks[0].Outputs[?OutputKey=='RepositoryUri'].OutputValue" \
  --output text \
  --region ${REGION})

# Build and push Docker image with timestamp tag and no cache
echo "Building and pushing Docker image to ECR with tag: ${IMAGE_TAG}..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}

# Always build with --no-cache to ensure fresh build
echo "Building Docker image with no cache..."
docker build --no-cache -t ${ECR_REPOSITORY_URI}:${IMAGE_TAG} .
docker tag ${ECR_REPOSITORY_URI}:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:latest

# Push both tags
echo "Pushing Docker image with tags: ${IMAGE_TAG} and latest..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}
docker push ${ECR_REPOSITORY_URI}:latest

# Deploy VPC
echo "Deploying VPC..."
aws cloudformation deploy \
  --template-file ./cloudformation/vpc.yaml \
  --stack-name "${STACK_PREFIX}-vpc" \
  --parameter-overrides \
    Environment=${ENVIRONMENT} \
  --capabilities CAPABILITY_IAM \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Get VPC outputs
VPC_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-vpc" \
  --query "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue" \
  --output text \
  --region ${REGION})

PUBLIC_SUBNET_1=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-vpc" \
  --query "Stacks[0].Outputs[?OutputKey=='PublicSubnet1'].OutputValue" \
  --output text \
  --region ${REGION})

PUBLIC_SUBNET_2=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-vpc" \
  --query "Stacks[0].Outputs[?OutputKey=='PublicSubnet2'].OutputValue" \
  --output text \
  --region ${REGION})

PRIVATE_SUBNET_1=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-vpc" \
  --query "Stacks[0].Outputs[?OutputKey=='PrivateSubnet1'].OutputValue" \
  --output text \
  --region ${REGION})

PRIVATE_SUBNET_2=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-vpc" \
  --query "Stacks[0].Outputs[?OutputKey=='PrivateSubnet2'].OutputValue" \
  --output text \
  --region ${REGION})

# Deploy DynamoDB table
echo "Deploying DynamoDB table..."
aws cloudformation deploy \
  --template-file ./cloudformation/database.yaml \
  --stack-name "${STACK_PREFIX}-db" \
  --parameter-overrides \
    Environment=${ENVIRONMENT} \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Get DynamoDB table name
DYNAMODB_TABLE=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-db" \
  --query "Stacks[0].Outputs[?OutputKey=='TableName'].OutputValue" \
  --output text \
  --region ${REGION})

# Deploy ECS cluster
echo "Deploying ECS cluster..."
aws cloudformation deploy \
  --template-file ./cloudformation/ecs-cluster.yaml \
  --stack-name "${STACK_PREFIX}-cluster" \
  --parameter-overrides \
    Environment=${ENVIRONMENT} \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Get ECS cluster name
ECS_CLUSTER=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-cluster" \
  --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
  --output text \
  --region ${REGION})

# Deploy ECS service with the new image tag
echo "Deploying ECS service with image tag: ${IMAGE_TAG}..."
aws cloudformation deploy \
  --template-file ./cloudformation/app-service.yaml \
  --stack-name "${STACK_PREFIX}-service" \
  --parameter-overrides \
    Environment=${ENVIRONMENT} \
    VpcId=${VPC_ID} \
    PublicSubnet1=${PUBLIC_SUBNET_1} \
    PublicSubnet2=${PUBLIC_SUBNET_2} \
    PrivateSubnet1=${PRIVATE_SUBNET_1} \
    PrivateSubnet2=${PRIVATE_SUBNET_2} \
    EcsCluster=${ECS_CLUSTER} \
    EcrRepository=${ECR_REPOSITORY_URI} \
    ImageTag=${IMAGE_TAG} \
    DynamoDBTable=${DYNAMODB_TABLE} \
  --capabilities CAPABILITY_IAM \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Force a new deployment if requested
if [ "$FORCE_DEPLOY" = "true" ]; then
  echo "Forcing a new deployment of the ECS service..."
  aws ecs update-service \
    --cluster ${ECS_CLUSTER} \
    --service ${STACK_PREFIX} \
    --force-new-deployment \
    --region ${REGION}
fi

# Get service URL
SERVICE_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-service" \
  --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" \
  --output text \
  --region ${REGION})

# Wait for service to stabilize
echo "Waiting for ECS service to stabilize..."
aws ecs wait services-stable \
  --cluster ${ECS_CLUSTER} \
  --services ${STACK_PREFIX} \
  --region ${REGION}

echo "====================================================="
echo "Deployment complete!"
echo "====================================================="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Deployment Summary:"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "Image Tag: ${IMAGE_TAG}"
echo "VPC ID: ${VPC_ID}"
if [ "${ENVIRONMENT}" == "prod" ]; then
  echo "Subnets: Private subnets with NAT Gateway"
else
  echo "Subnets: Public subnets with direct internet access"
fi
echo "DynamoDB Table: ${DYNAMODB_TABLE}"
echo "ECS Cluster: ${ECS_CLUSTER}"
echo "ECR Repository: ${ECR_REPOSITORY_URI}"
echo ""
echo "To force a new deployment in the future, run:"
echo "./deploy.sh ${ENVIRONMENT} ${REGION} true"
echo "====================================================="

# Open the service URL in the default browser if on a desktop
if command -v xdg-open &> /dev/null; then
  echo "Opening service URL in browser..."
  xdg-open "${SERVICE_URL}"
elif command -v open &> /dev/null; then
  echo "Opening service URL in browser..."
  open "${SERVICE_URL}"
else
  echo "Visit the service URL in your browser: ${SERVICE_URL}"
fi
