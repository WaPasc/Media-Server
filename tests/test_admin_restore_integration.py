"""Integration test for /api/admin/export → /api/admin/restore round-trip.

This test runs against a REAL Postgres instance and is destructive on the
target database (it drops and recreates tables). To prevent accidents against
a developer's live mediadb, the test is gated on the TEST_POSTGRES_URL env
var: it skips entirely unless that variable is set, and the route is
monkeypatched to use TEST_POSTGRES_URL, never the real POSTGRES_URL.

In CI we set TEST_POSTGRES_URL to point at the workflow's postgres service
container. Locally, run with:

    TEST_POSTGRES_URL=postgresql://user:pw@localhost:5432/test_streamservice \\
        pytest tests/test_admin_restore_integration.py -v

Make sure that database is dedicated to tests, its contents will be wiped.
"""

import os
import shutil
import uuid
from typing import Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

TEST_DB_URL = os.getenv('TEST_POSTGRES_URL')

pytestmark = [
    pytest.mark.skipif(
        not TEST_DB_URL,
        reason='TEST_POSTGRES_URL not set, integration test skipped',
    ),
    pytest.mark.skipif(
        shutil.which('pg_dump') is None or shutil.which('pg_restore') is None,
        reason='pg_dump/pg_restore not installed on this host',
    ),
]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Critical: redirect the route's POSTGRES_URL to the test DB. This ensures
    # the route can never reach the developer's real mediadb during this test.
    assert TEST_DB_URL is not None  # narrowed by the skipif at module level
    monkeypatch.setenv('POSTGRES_URL', TEST_DB_URL)
    monkeypatch.setenv('ADMIN_TOKEN', 'integration-test-token')

    from app.main import app

    return TestClient(app)


@pytest.fixture
def fresh_table() -> Iterator[str]:
    """Create a uniquely-named table with seed rows; drop it on teardown.

    Using a unique table name per test run means we don't collide with the
    application schema even if someone points TEST_POSTGRES_URL at a busy DB.
    """
    assert TEST_DB_URL is not None
    table = f'export_test_{uuid.uuid4().hex[:8]}'
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE TABLE {table} (id INT PRIMARY KEY, label TEXT)')
            cur.execute(
                f"INSERT INTO {table} VALUES (1, 'alpha'), (2, 'beta'), (3, 'gamma')"
            )
        conn.commit()

    yield table

    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP TABLE IF EXISTS {table}')
        conn.commit()


def _row_count(table: str) -> int:
    assert TEST_DB_URL is not None
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {table}')
            row = cur.fetchone()
            assert row is not None
            return row[0]


def _table_exists(table: str) -> bool:
    assert TEST_DB_URL is not None
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM information_schema.tables '
                'WHERE table_schema = current_schema() AND table_name = %s',
                (table,),
            )
            return cur.fetchone() is not None


def test_export_restore_round_trip(client: TestClient, fresh_table: str) -> None:
    table = fresh_table
    headers = {'X-Admin-Token': 'integration-test-token'}

    # 1. Export, dump the current DB (including our fresh_table).
    export_response = client.get('/api/admin/export', headers=headers)
    assert export_response.status_code == 200
    dump_bytes = export_response.content
    assert dump_bytes.startswith(b'PGDMP'), 'Custom-format pg_dump magic missing'
    assert len(dump_bytes) > 100

    # 2. Mutate the live data so we can prove the restore puts it back.
    with psycopg.connect(TEST_DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DELETE FROM {table}')
        conn.commit()
    assert _row_count(table) == 0

    # 3. Restore, uploading the dump should re-create the rows.
    restore_response = client.post(
        '/api/admin/restore',
        headers=headers,
        files={
            'file': (
                'backup.dump',
                dump_bytes,
                'application/octet-stream',
            )
        },
    )
    assert restore_response.status_code == 200, restore_response.text

    # 4. Verify the data is back.
    assert _table_exists(table)
    assert _row_count(table) == 3
