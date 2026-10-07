# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Install system dependencies required by geopandas / pyogrio / GDAL
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        libproj-dev \
        proj-data \
        proj-bin \
        libspatialindex-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer-cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ app/

# Create storage directory
RUN mkdir -p /app/uploads

# Runtime configuration
ENV DATABASE_URL="sqlite:///./geospatial.db" \
    STORAGE_DIR="/app/uploads" \
    MAX_UPLOAD_MB="50" \
    MAX_UNCOMPRESSED_MB="200" \
    CORS_ORIGINS='["http://localhost:3000"]'

EXPOSE 8000

# Non-root user for security
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
