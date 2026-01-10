.PHONY: help build up down restart logs clean test rebuild shell-backend shell-frontend install-backend install-frontend analyze-all

# Default target
help:
	@echo "Available commands:"
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
