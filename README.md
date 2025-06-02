# Cloud Defender - AWS ECS Game

This project demonstrates a fun, interactive game deployed on Amazon ECS (Elastic Container Service) following AWS Well-Architected best practices.

## Game Overview

Cloud Defender is a space shooter game where players defend AWS cloud resources from various threats. The game features:

- A browser-based interface for playing a simplified version
- A downloadable Python client for the full gaming experience with graphics and sound
- High score tracking with DynamoDB
- Serverless deployment on ECS with Fargate

## Architecture Overview

The application is built with the following components:

- **Flask API**: A Python-based web server that provides game logic and high score tracking
- **Pygame**: Python gaming library for the client-side experience
- **DynamoDB**: NoSQL database for storing high scores
- **ECS with Fargate**: Serverless container orchestration
- **Application Load Balancer**: For distributing traffic to containers
- **CloudWatch**: For monitoring and logging
- **X-Ray**: For distributed tracing
- **AWS IAM**: For secure access control

The infrastructure is defined as code using AWS CloudFormation templates.

## Well-Architected Pillars Implementation

### Operational Excellence
- Infrastructure as Code (CloudFormation)
- Centralized logging with CloudWatch Logs
- X-Ray for distributed tracing
- Health checks and graceful task replacement

### Security
- Least privilege IAM roles
- Security groups with minimal access
- Private subnets for containers
- VPC endpoints for AWS services
- Encryption at rest and in transit

### Reliability
- Multi-AZ deployment
- Auto-scaling based on metrics
- Health checks and graceful task replacement
- Load balancing across tasks

### Performance Efficiency
- Right-sized container resources
- Auto-scaling based on CPU utilization
- CloudWatch metrics for performance monitoring

### Cost Optimization
- Fargate for serverless container execution
- Auto-scaling to match demand
- Pay-per-request DynamoDB option
- Single NAT Gateway for all private subnets

## Project Structure

```
.
├── app.py                  # Flask application code with game logic
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container definition
├── deploy.sh               # Deployment script
├── assets/                 # Game assets directory
├── cloudformation/         # CloudFormation templates
│   ├── vpc.yaml            # VPC and networking
│   ├── database.yaml       # DynamoDB table
│   ├── ecr.yaml            # ECR repository
│   ├── ecs-cluster.yaml    # ECS cluster
│   └── app-service.yaml    # ECS service and task definition
└── README.md               # This file
```

## Game Endpoints

The application provides the following endpoints:

- `/`: Main game interface
- `/health`: Health check endpoint
- `/download`: Instructions for downloading the game client
- `/scores`: API for high scores (GET to retrieve, POST to submit)
- `/game/start`: Start a new game session
- `/game/status`: Get current game state
- `/game/move`: Move the player
- `/game/shoot`: Fire a bullet

## Deployment Instructions

### Prerequisites

- AWS CLI installed and configured
- Docker installed
- jq installed (for JSON parsing)

### Deployment Steps

1. Clone this repository:
   ```
   git clone <repository-url>
   cd aws-qcli-game
   ```

2. Make the deployment script executable:
   ```
   chmod +x deploy.sh
   ```

3. Run the deployment script:
   ```
   ./deploy.sh [environment] [region]
   ```
   
   Where:
   - `environment` is optional (default: dev)
   - `region` is optional (default: us-east-1)

   Example:
   ```
   ./deploy.sh prod us-west-2
   ```

4. The script will:
   - Create an S3 bucket for CloudFormation templates
   - Deploy the ECR repository
   - Build and push the Docker image
   - Deploy the VPC and networking components
   - Deploy the DynamoDB table
   - Deploy the ECS cluster
   - Deploy the ECS service and related resources
   - Output the service URL

## Playing the Game

### Browser Version

1. Open the service URL in your web browser
2. Click "Start Game" to play the simplified browser version
3. Submit your score when the game ends

### Full Client Version

1. Install Python 3.9+ and required packages:
   ```
   pip install pygame numpy requests pillow
   ```

2. Download the game client code from the `/download` page
3. Save it as `cloud_defender.py`
4. Update the `SERVER_URL` in the code to match your deployed service URL
5. Run the game:
   ```
   python cloud_defender.py
   ```

## Monitoring and Observability

The application is configured with:

- CloudWatch Logs for centralized logging
- CloudWatch Metrics for monitoring
- CloudWatch Alarms for alerting on high CPU/memory usage
- X-Ray for distributed tracing

You can access these in the AWS Management Console under the respective services.

## Cleanup

To avoid incurring charges, delete the CloudFormation stacks when you're done:

```bash
aws cloudformation delete-stack --stack-name cloud-defender-<environment>-service --region <region>
aws cloudformation delete-stack --stack-name cloud-defender-<environment>-cluster --region <region>
aws cloudformation delete-stack --stack-name cloud-defender-<environment>-db --region <region>
aws cloudformation delete-stack --stack-name cloud-defender-<environment>-vpc --region <region>
aws cloudformation delete-stack --stack-name cloud-defender-<environment>-ecr --region <region>
```

Also, delete the S3 bucket created for CloudFormation templates:

```bash
aws s3 rb s3://cloud-defender-<environment>-cfn-<account-id> --force
```
