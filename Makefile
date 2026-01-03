# Makefile for common development tasks

.PHONY: help setup test format lint type-check quality clean run build docker

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	pip install -e ".[dev]"
	cd web && npm install
	pre-commit install

test: ## Run all tests
	pytest --cov=src --cov-report=html

format: ## Format code with black and isort
	black src tests server.py
	isort src tests server.py

lint: ## Run linters
	flake8 src tests server.py
	cd web && npm run lint

type-check: ## Run type checking
	mypy src

quality: ## Run all code quality checks
	python check_quality.py

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache/ .mypy_cache/ htmlcov/
	rm -rf web/dist/ web/node_modules/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run-backend: ## Start backend server
	python -m uvicorn server:app --reload --port 8000

run-frontend: ## Start frontend dev server
	cd web && npm run dev

run-both: ## Start both backend and frontend
	@echo "Starting backend and frontend..."
	@(python -m uvicorn server:app --reload --port 8000 &)
	@(cd web && npm run dev)

build-frontend: ## Build frontend for production
	cd web && npm run build

build-windows: ## Build Windows executable
	powershell -ExecutionPolicy Bypass -File manage.ps1 windows-build

docker-build: ## Build Docker image
	docker build -t pennerbot:latest .

docker-run: ## Run Docker container
	docker run -p 8000:8000 -p 1420:1420 pennerbot:latest

security-check: ## Run security checks
	bandit -r src -f json -o security-report.json
	safety check

performance: ## Get performance metrics
	curl http://localhost:8000/api/metrics/performance | jq

cache-stats: ## Get cache statistics
	curl http://localhost:8000/api/metrics/performance | jq '.cache'

cache-clear: ## Clear application cache
	curl -X POST http://localhost:8000/api/cache/clear

maintenance: ## Run maintenance cleanup
	curl -X POST http://localhost:8000/api/maintenance/cleanup | jq
