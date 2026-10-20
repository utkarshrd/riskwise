# RiskWise Development Makefile

.PHONY: help setup test verify lint run-backend run-frontend clean docker-build docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make setup         - Initialize virtual environments and install dependencies"
	@echo "  make test          - Run backend and frontend test suites"
	@echo "  make verify        - Run backend end-to-end wiring verification suite"
	@echo "  make lint          - Run linters (ruff, eslint)"
	@echo "  make run-backend   - Start FastAPI backend dev server"
	@echo "  make run-frontend  - Start Next.js frontend dev server"
	@echo "  make docker-build  - Build Docker containers for backend and frontend"
	@echo "  make docker-up     - Start backend and frontend via Docker Compose"
	@echo "  make docker-down   - Stop Docker containers"
	@echo "  make docker-logs   - Stream Docker container logs"
	@echo "  make clean         - Remove temp build and cache files"

setup:
	@echo "Setting up backend..."
	cd backend && python -m pip install -r requirements.txt
	alembic upgrade head
	python scripts/register_models.py
	@echo "Setting up frontend..."
	cd frontend && npm install

verify:
	@echo "Running backend wiring and provenance verification suite..."
	python scripts/verify_wiring.py

test:
	@echo "Running backend tests..."
	cd backend && pytest tests/ -v
	@echo "Running frontend tests..."
	cd frontend && npm test --if-present

lint:
	@echo "Linting backend..."
	cd backend && ruff check .
	@echo "Linting frontend..."
	cd frontend && npm run lint

run-backend:
	uvicorn backend.app.main:app --reload --port 8000

run-frontend:
	cd frontend && npm run dev

clean:
	rm -rf backend/__pycache__ backend/.pytest_cache frontend/.next

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

