#!/bin/sh
# Container start-up: prepare the database and retrieval index, then run the API.
# Everything is idempotent, so restarting the container is safe.
set -e

python /app/docker/prepare.py

exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
