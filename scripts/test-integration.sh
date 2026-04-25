#!/bin/bash

# Runs the destructive admin export/restore round-trip test against an
# ephemeral database that lives on the running postgres-stream container.
#
# Why this script exists:
#   - The integration test needs `pg_dump` / `pg_restore` matching the server
#     version (17). Those binaries live inside the rebuilt ms-backend image,
#     not on your host. Running the test in-container avoids requiring you to
#     install postgresql-client-17 on your laptop.
#   - We isolate the test on a uniquely-named throwaway database created and
#     dropped by this script, so the live `mediadb` is never touched.
#
# Prereqs: `docker compose up -d` must be running (postgres-stream + ms-backend).
# Safe to re-run: cleanup happens unconditionally on exit.

set -euo pipefail

cd "$(dirname "$0")/.."

# Read DB credentials from .env if present, otherwise fall back to the
# defaults baked into docker-compose.yml.
DB_USER="${POSTGRES_USER:-streamer}"
DB_PASSWORD="${POSTGRES_PASSWORD:-streamerWP14!}"
DB_HOST_INTERNAL="database_postgres"   # compose service name (container DNS)
TEST_DB="test_admin_roundtrip_$$"      # $$ = shell PID, unique per run

cleanup() {
  echo ""
  echo "[cleanup] Dropping ephemeral database $TEST_DB"
  docker exec postgres-stream psql -U "$DB_USER" -d postgres \
    -c "DROP DATABASE IF EXISTS $TEST_DB WITH (FORCE);" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[1/4] Ensuring ms-backend image has pg_dump (rebuild if Dockerfile changed)..."
docker compose build ms-backend

echo "[2/4] Creating ephemeral test database: $TEST_DB"
docker exec postgres-stream psql -U "$DB_USER" -d postgres \
  -c "CREATE DATABASE $TEST_DB;" >/dev/null

echo "[3/4] Running integration test in ms-backend container..."
docker compose run -u root --rm \
  -v "./tests:/app/tests" \
  -v "./src:/app/src" \
  -v "./pyproject.toml:/app/pyproject.toml" \
  -e "TEST_POSTGRES_URL=postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST_INTERNAL}:5432/${TEST_DB}" \
  ms-backend bash -c "
  /opt/venv/bin/python -m pip install -q -e '.[test]'
  PYTHONPATH=/app/src /opt/venv/bin/python -m pytest \
    /app/tests/test_admin_restore_integration.py -s -v
"

echo "[4/4] Done."
