# Heyaaashu Studio — Unified Production Cloud Dockerfile (Render)

# Stage 1: Build React Visual Content Studio
FROM node:20-alpine AS frontend-builder

WORKDIR /app/apps/message-builder
COPY apps/message-builder/package.json apps/message-builder/package-lock.json ./
RUN npm ci

COPY apps/message-builder/ ./
ENV NODE_ENV=production
RUN npm run build

# Stage 2: Unified Python API, Webhook & Frontend Server
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy built frontend assets
COPY --from=frontend-builder /app/apps/message-builder/dist ./apps/message-builder/dist

# Copy application source code
COPY packages/ ./packages/
COPY apps/ ./apps/
COPY test-data/ ./test-data/

# Create data directory for local fallback
RUN mkdir -p /app/data

EXPOSE 8000

CMD ["python", "-m", "apps.api.server"]
