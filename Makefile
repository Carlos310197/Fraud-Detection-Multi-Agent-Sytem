.PHONY: help build up down restart logs clean test rebuild shell-backend shell-frontend install-backend install-frontend analyze-all aws-build aws-deploy aws-upload-data aws-logs aws-delete

# Default target
help:
	@echo "Available commands:"
	@echo ""
	@echo "Docker (Local Development):"
	@echo "  make build          - Build Docker images"
	@echo "  make up             - Start all services"
	@echo "  make down           - Stop all services"
	@echo "  make restart        - Restart all services"
	@echo "  make rebuild        - Rebuild and restart (no cache)"
	@echo "  make logs           - View logs (all services)"
	@echo "  make logs-backend   - View backend logs only"
	@echo "  make logs-frontend  - View frontend logs only"
	@echo "  make clean          - Stop services and remove volumes"
	@echo "  make test-backend   - Run backend tests"
	@echo "  make shell-backend  - Open bash shell in backend container"
	@echo "  make shell-frontend - Open bash shell in frontend container"
	@echo "  make install-backend - Install backend dependencies locally"
	@echo "  make install-frontend - Install frontend dependencies locally"
	@echo "  make ps             - Show running containers"
	@echo "  make prune          - Remove all stopped containers and unused images"
	@echo ""
	@echo "AWS Deployment:"
	@echo "  make aws-build      - Build Lambda container image"
	@echo "  make aws-deploy     - Deploy to AWS with SAM (guided)"
	@echo "  make aws-upload-data - Upload input data to S3 bucket"
	@echo "  make aws-logs       - View Lambda function logs"
	@echo "  make aws-delete     - Delete AWS stack"
	@echo ""
	@echo "Frontend Deployment:"
	@echo "  make frontend-deploy - Deploy frontend to AWS S3 + CloudFront"
	@echo "  make frontend-build  - Build frontend locally"
	@echo "  make frontend-update - Update existing frontend deployment"
	@echo "  make frontend-info   - Show frontend deployment info"
	@echo "  make frontend-delete - Delete frontend deployment"

# Build Docker images
build:
	docker compose build

# Start all services
up:
	docker compose up

# Start services in detached mode
up-d:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Restart all services
restart: down up

# Rebuild
rebuild:
	docker compose down
	docker compose build
	docker compose up

# Rebuild without cache and restart
rebuild-no-cache:
	docker compose down
	docker compose build --no-cache
	docker compose up

# Rebuild backend only
rebuild-backend:
	docker compose build --no-cache backend
	docker compose up -d backend

# Rebuild frontend only
rebuild-frontend:
	docker compose build --no-cache frontend
	docker compose up -d frontend

# View logs for all services
logs:
	docker compose logs -f

# View backend logs
logs-backend:
	docker compose logs -f backend

# View frontend logs
logs-frontend:
	docker compose logs -f frontend

# Stop services and remove volumes
clean:
	docker compose down -v
	@echo "Cleaned up containers and volumes"

# Deep clean - remove images too
clean-all: clean
	docker compose down --rmi all
	@echo "Removed all images"

# Run backend tests
test-backend:
	cd backend && pytest

# Open bash shell in backend container
shell-backend:
	docker compose exec backend /bin/bash

# Open bash shell in frontend container
shell-frontend:
	docker compose exec frontend /bin/sh

# Install backend dependencies locally (for IDE support)
install-backend:
	cd backend && pip install -r requirements.txt

# Install frontend dependencies locally (for IDE support)
install-frontend:
	cd frontend && npm install

# Show running containers
ps:
	docker compose ps

# Prune Docker system
prune:
	docker system prune -a --volumes -f

# Health check
health:
	@echo "Checking backend health..."
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "Backend not responding"
	@echo "\nChecking frontend..."
	@curl -s http://localhost:5173 > /dev/null && echo "Frontend is up" || echo "Frontend not responding"

# Quick start (build and run in background)
start: build up-d
	@echo "Services started in background"
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "Run 'make logs' to view logs"

# Stop and remove everything
stop: down
	@echo "All services stopped"

# ============================================
# AWS Deployment Commands
# ============================================

# Build Lambda container image
aws-build:
	@echo "Building Lambda container image..."
	cd backend && sam build

# Deploy to AWS (first time or updates)
aws-deploy:
	@echo "Deploying to AWS with SAM..."
	@echo "Note: You will be prompted for stack name, region, and other parameters"
	cd backend && sam build && sam deploy --guided

# Quick deploy (skip guided prompts, use samconfig.toml)
aws-deploy-quick:
	@echo "Deploying to AWS (using saved config)..."
	cd backend && sam build && sam deploy

# Upload sample data to S3 bucket
aws-upload-data:
	@echo "Uploading sample data to S3..."
	@read -p "Enter S3 bucket name: " bucket; \
	aws s3 cp .storage/input/transactions.csv s3://$$bucket/transactions.csv && \
	aws s3 cp .storage/input/customer_behavior.csv s3://$$bucket/customer_behavior.csv && \
	aws s3 cp .storage/input/fraud_policies.json s3://$$bucket/fraud_policies.json && \
	echo "Data uploaded to s3://$$bucket/"

# View CloudWatch logs for Lambda function
aws-logs:
	@echo "Fetching Lambda logs..."
	@read -p "Enter stack name (default: fraud-detection): " stack; \
	stack=$${stack:-fraud-detection}; \
	function_name=$$(aws cloudformation describe-stacks --stack-name $$stack --query "Stacks[0].Outputs[?OutputKey=='FunctionName'].OutputValue" --output text); \
	sam logs -n $$function_name --tail

# Delete AWS stack
aws-delete:
	@echo "WARNING: This will delete the entire AWS stack including all data!"
	@read -p "Enter stack name to delete: " stack; \
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		aws cloudformation delete-stack --stack-name $$stack; \
		echo "Stack deletion initiated. Check AWS Console for progress."; \
	else \
		echo "Deletion cancelled."; \
	fi

# Get stack outputs (API URL, bucket name, etc.)
aws-outputs:
	@read -p "Enter stack name (default: fraud-detection): " stack; \
	stack=$${stack:-fraud-detection}; \
	aws cloudformation describe-stacks --stack-name $$stack --query "Stacks[0].Outputs" --output table
# ============================================
# Frontend Deployment Commands
# ============================================

# Deploy frontend to AWS S3 + CloudFront
frontend-deploy:
	@echo "Deploying frontend to AWS S3 + CloudFront..."
	./deploy-frontend.sh

# Build frontend locally
frontend-build:
	@echo "Building frontend..."
	cd frontend && npm install && npm run build

# Update frontend (rebuild and redeploy)
frontend-update: frontend-build
	@echo "Updating frontend deployment..."
	@stack_name="fraud-detection-frontend"; \
	bucket_name=$$(aws cloudformation describe-stacks --stack-name $$stack_name --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text); \
	distribution_id=$$(aws cloudformation describe-stacks --stack-name $$stack_name --query 'Stacks[0].Outputs[?OutputKey==`DistributionId`].OutputValue' --output text); \
	echo "Uploading to bucket: $$bucket_name"; \
	aws s3 sync frontend/dist/ s3://$$bucket_name --delete; \
	echo "Invalidating CloudFront cache..."; \
	aws cloudfront create-invalidation --distribution-id $$distribution_id --paths "/*" > /dev/null; \
	echo "Frontend updated successfully!"

# Get frontend deployment info
frontend-info:
	@stack_name="fraud-detection-frontend"; \
	echo "Frontend Deployment Info:"; \
	aws cloudformation describe-stacks --stack-name $$stack_name --query "Stacks[0].Outputs" --output table

# Delete frontend deployment
frontend-delete:
	@echo "WARNING: This will delete the frontend deployment!"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		stack_name="fraud-detection-frontend"; \
		bucket_name=$$(aws cloudformation describe-stacks --stack-name $$stack_name --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' --output text 2>/dev/null || echo ""); \
		if [ -n "$$bucket_name" ]; then \
			echo "Emptying S3 bucket: $$bucket_name"; \
			aws s3 rm s3://$$bucket_name --recursive; \
		fi; \
		echo "Deleting CloudFormation stack..."; \
		aws cloudformation delete-stack --stack-name $$stack_name; \
		echo "Frontend deletion initiated."; \
	else \
		echo "Deletion cancelled."; \
	fi