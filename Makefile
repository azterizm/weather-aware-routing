.PHONY: install dev-backend dev-frontend test test-backend test-frontend lint format build

install:
	cd backend && uv sync
	cd frontend && npm ci

dev-backend:
	cd backend && DJANGO_DEBUG=1 uv run python manage.py runserver 127.0.0.1:8000

dev-frontend:
	cd frontend && npm run dev

test: test-backend test-frontend

test-backend:
	cd backend && uv run pytest

test-frontend:
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && npm run lint && npm run typecheck && npm run format:check

format:
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && npm run format

build:
	cd frontend && npm run build
