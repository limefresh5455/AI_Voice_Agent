.PHONY: help build up down logs shell test clean dev-setup

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-app: ## View logs from app only
	docker-compose logs -f app

shell: ## Open shell in app container
	docker-compose exec app /bin/bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U ai_voice -d ai_voice

test: ## Run tests inside container
	docker-compose exec app pytest

clean: ## Remove containers, volumes, and images
	docker-compose down -v
	docker system prune -f

dev-setup: ## Initial setup for development
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.docker..."; \
		cp .env.docker .env; \
		echo "⚠️  Please edit .env and add your API keys!"; \
	else \
		echo ".env already exists"; \
	fi

rebuild: ## Rebuild and restart services
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

restart: ## Restart all services
	docker-compose restart

status: ## Show status of all services
	docker-compose ps

dev-redis: ## Start only Redis for local development
	docker-compose up -d redis

dev-postgres: ## Start only PostgreSQL for local development
	docker-compose up -d postgres

prod-deploy: ## Deploy to production
	@echo "Building production images..."
	docker-compose -f docker-compose.yml build
	@echo "Starting services..."
	docker-compose -f docker-compose.yml up -d
	@echo "Deployment complete!"

health: ## Check health of all services
	@echo "App health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "App not responding"
	@echo "\nPostgreSQL:"
	@docker-compose exec postgres pg_isready -U ai_voice || echo "PostgreSQL not ready"
	@echo "\nRedis:"
	@docker-compose exec redis redis-cli ping || echo "Redis not responding"
