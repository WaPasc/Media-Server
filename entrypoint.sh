#!/bin/bash
set -e

echo "Starting Media Server backend..."

# Run Alembic database migrations automatically
# This ensures Postgres DB is perfectly up to date before starting
echo "Running database migrations..."
cd src
alembic upgrade head
cd ..

# Start the FastAPI application using Uvicorn
echo "Starting Uvicorn server..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --proxy-headers