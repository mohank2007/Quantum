# ==========================================
# Stage 1: Build Frontend (React + Vite SPA)
# ==========================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Install frontend dependencies
COPY Diseases_Detection_Paltform/frontend/package*.json ./
RUN npm install

# Copy frontend source code and compile production assets
COPY Diseases_Detection_Paltform/frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend + UI
# ==========================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    FRONTEND_DIST=/app/frontend_dist

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python backend dependencies
COPY Diseases_Detection_Paltform/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application source code
COPY Diseases_Detection_Paltform/backend/ .

# Copy compiled frontend production assets from Stage 1
COPY --from=frontend-builder /frontend/dist /app/frontend_dist

# Ensure artifacts directory exists with proper permissions
RUN mkdir -p /app/artifacts

EXPOSE 8000

# Default command starts Uvicorn server with dynamic port support (Render/Docker)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
