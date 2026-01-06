# Multi-stage Dockerfile für PennerBot
# Stage 1: Build Frontend (React + Vite)
FROM node:20-alpine AS frontend-builder

WORKDIR /app/web

# Copy package files
COPY web/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY web/ ./

# Build argument für API URL (optional)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build frontend
RUN npm run build

# Stage 2: Python Backend + Serve Frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml ./
COPY server.py ./
COPY launcher.py ./
COPY docker-start.py ./

# Copy source code
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy built frontend from previous stage
COPY --from=frontend-builder /app/web/dist ./web/dist
COPY web/serve.py ./web/

# Create directory for database
RUN mkdir -p /app/data

# Expose ports
# 8000 - FastAPI Backend
# 1420 - Frontend Server
EXPOSE 8000 1420

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DATABASE_PATH=/app/data/pennergame.db

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/health', timeout=5)" || exit 1

# Start both backend and frontend with Docker-specific script
CMD ["python", "docker-start.py"]
