#!/bin/bash

# Runs the unit / non-destructive test suite inside an ephemeral container.
# The admin export/restore round-trip test (test_admin_restore_integration.py)
# auto-skips here because TEST_POSTGRES_URL is not set, to run that one,
# use scripts/test-integration.sh instead.

# Ensure the script always runs from the project root
cd "$(dirname "$0")/.."

echo "Spinning up ephemeral test container..."

# Run the temporary container AS ROOT (-u root) to bypass venv permissions.
# Dynamically mount local source and test files (-v) so the container can see them
docker compose run -u root --rm \
  -v "./tests:/app/tests" \
  -v "./src:/app/src" \
  -v "./pyproject.toml:/app/pyproject.toml" \
  ms-backend bash -c "
  echo 'Installing test dependencies dynamically...'
  /opt/venv/bin/python -m pip install -q -e '.[test]'

  echo 'Running unit test suite...'
  PYTHONPATH=/app/src /opt/venv/bin/python -m pytest /app/tests/ \
    --ignore=/app/tests/test_admin_restore_integration.py \
    -s -v
"

echo "Testing complete. Ephemeral container destroyed."
