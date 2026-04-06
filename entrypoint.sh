#!/bin/bash
set -e

echo "Starting Media Server backend..."

# Run Alembic database migrations automatically
# We run this from the root (/app) so it can read pyproject.toml!
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application using Uvicorn
# We use python -m to ensure it finds everything in the venv
echo "Starting Uvicorn server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers