#!/bin/bash
set -e

# Default values
ENVIRONMENT=${1:-dev}
REGION=${2:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
STACK_PREFIX="cloud-defender-${ENVIRONMENT}"
S3_BUCKET="${STACK_PREFIX}-cfn-${ACCOUNT_ID}"
ECR_REPOSITORY_NAME="${STACK_PREFIX}"

echo "Deploying Cloud Defender Game to ${ENVIRONMENT} environment in ${REGION} region"

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

# Build and push Docker image
echo "Building and pushing Docker image to ECR..."
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}
docker build -t ${ECR_REPOSITORY_URI}:latest .
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

# Deploy ECS service
echo "Deploying ECS service..."
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
    DynamoDBTable=${DYNAMODB_TABLE} \
  --capabilities CAPABILITY_IAM \
  --region ${REGION} \
  --no-fail-on-empty-changeset

# Get service URL
SERVICE_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_PREFIX}-service" \
  --query "Stacks[0].Outputs[?OutputKey=='ServiceUrl'].OutputValue" \
  --output text \
  --region ${REGION})

echo "Deployment complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Deployment Summary:"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "VPC ID: ${VPC_ID}"
if [ "${ENVIRONMENT}" == "prod" ]; then
  echo "Subnets: Private subnets with NAT Gateway"
else
  echo "Subnets: Public subnets with direct internet access"
fi
echo "DynamoDB Table: ${DYNAMODB_TABLE}"
echo "ECS Cluster: ${ECS_CLUSTER}"
echo "ECR Repository: ${ECR_REPOSITORY_URI}"
