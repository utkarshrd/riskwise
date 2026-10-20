FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# System runtime dependencies:
# - build-essential for compiling C/C++ extensions
# - libgomp1: OpenMP runtime required by XGBoost and scikit-learn
# - curl: required for Docker health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Pre-create standard directories
RUN mkdir -p /app/db /app/data /app/artifacts /app/knowledge

# Install pinned Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application source code, Alembic migrations config, and scripts
COPY backend/ /app/backend/
COPY alembic.ini /app/alembic.ini
COPY scripts/ /app/scripts/

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
