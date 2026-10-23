# Build from the repository root:  docker build -f backend/Dockerfile -t riskwise-backend .
# The image is self-contained: trained credit models, retrieval index, knowledge corpus,
# market snapshots and the drift baseline are copied in, so nothing needs mounting at run time.
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# libgomp1: OpenMP runtime for XGBoost / scikit-learn; curl: health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY ml/ /app/ml/
COPY scripts/ /app/scripts/
COPY docker/ /app/docker/
COPY alembic.ini /app/alembic.ini
COPY knowledge/ /app/knowledge/
COPY artifacts/ /app/artifacts/
COPY data/ /app/data/

# Fail the build early, with a readable reason, if the gitignored model files are not in the build context
RUN if ! ls /app/artifacts/models/*.joblib >/dev/null 2>&1; then \
      echo "ERROR: artifacts/models/*.joblib not found in the build context." >&2; \
      echo "Get the trained model files (see docs/DOCKER.md) or load the prebuilt image tar instead of building." >&2; \
      exit 1; \
    fi \
    && if [ ! -f /app/data/processed/credit_indian_cleaned.csv ]; then \
      echo "WARNING: data/processed/credit_indian_cleaned.csv missing; drift monitoring will return 503." >&2; \
    fi \
    && sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && chmod +x /app/docker/entrypoint.sh \
    && mkdir -p /app/db

EXPOSE 8000

CMD ["/app/docker/entrypoint.sh"]
