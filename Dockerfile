# syntax=docker/dockerfile:1

# --- Stage 1: build the React SPA -------------------------------------------------------
FROM node:24-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Django API + built SPA, served by gunicorn and WhiteNoise -------------------
FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    FRONTEND_DIST=/app/frontend_dist
COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock backend/.python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend_dist
# Pre-compress the SPA (Brotli + gzip) so WhiteNoise serves compressed assets.
RUN python -m whitenoise.compress -q /app/frontend_dist

RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000
# Heroku (and most PaaS) provide $PORT. gthread workers suit this I/O-bound API.
CMD gunicorn config.wsgi --bind 0.0.0.0:${PORT:-8000} --worker-class gthread \
    --workers ${WEB_CONCURRENCY:-2} --threads 4 --timeout 30 --access-logfile -
