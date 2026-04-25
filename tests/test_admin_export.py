"""Unit tests for /api/admin export and restore.

These tests never touch a real database, pg_dump and pg_restore are mocked at
the subprocess layer, and POSTGRES_URL points at a dummy host the code never
contacts. Safe to run anywhere, including against a workstation with a live
mediadb.
"""

from asyncio import StreamReader
from asyncio.subprocess import Process
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.main import app


@pytest.fixture(autouse=True)
def _admin_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Every test in this module assumes a configured admin token and a
    # syntactically valid POSTGRES_URL. Individual tests can override.
    monkeypatch.setenv('ADMIN_TOKEN', 'test-token-secret')
    monkeypatch.setenv('POSTGRES_URL', 'postgresql://user:pw@dummy-host:5432/dummy-db')


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ──────────────────────────────────────────────────────────────────────────
# Auth gate
# ──────────────────────────────────────────────────────────────────────────


def test_export_requires_admin_token(client: TestClient) -> None:
    response = client.get('/api/admin/export')
    assert response.status_code == 401


def test_export_rejects_wrong_token(client: TestClient) -> None:
    response = client.get('/api/admin/export', headers={'X-Admin-Token': 'wrong'})
    assert response.status_code == 401


def test_export_disabled_when_admin_token_unset(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv('ADMIN_TOKEN', raising=False)
    response = client.get('/api/admin/export', headers={'X-Admin-Token': 'anything'})
    assert response.status_code == 503


def test_restore_requires_admin_token(client: TestClient) -> None:
    response = client.post(
        '/api/admin/restore',
        files={'file': ('x.dump', b'', 'application/octet-stream')},
    )
    assert response.status_code == 401


# ──────────────────────────────────────────────────────────────────────────
# Export, happy path with mocked pg_dump
# ──────────────────────────────────────────────────────────────────────────


def _fake_pg_dump_proc(payload: bytes, returncode: int = 0) -> AsyncMock:
    """Build a mock object that quacks like asyncio.subprocess.Process for
    the streaming-export code path.

    `spec=Process` / `spec=StreamReader` make the mocks reject any attribute
    that isn't on the real class, so a typo or a future API drift in the
    route raises AttributeError at test time instead of silently inventing
    the attribute on the mock.
    """
    proc = AsyncMock(spec=Process)
    proc.returncode = returncode

    stdout = AsyncMock(spec=StreamReader)
    stdout_chunks = [payload, b'']  # second read signals EOF

    async def read(_n: int) -> bytes:
        return stdout_chunks.pop(0) if stdout_chunks else b''

    stdout.read = read
    proc.stdout = stdout

    stderr = AsyncMock(spec=StreamReader)
    stderr.read = AsyncMock(return_value=b'')
    proc.stderr = stderr

    proc.wait = AsyncMock(return_value=returncode)
    proc.kill = lambda: None
    return proc


def test_export_streams_dump_payload(client: TestClient, mocker: MockerFixture) -> None:
    fake_dump = b'PGDMP\x00fake-dump-bytes'
    proc = _fake_pg_dump_proc(fake_dump)

    mocker.patch('app.api.routes.admin.shutil.which', return_value='/usr/bin/pg_dump')
    mocker.patch(
        'app.api.routes.admin.asyncio.create_subprocess_exec',
        AsyncMock(return_value=proc),
    )

    response = client.get(
        '/api/admin/export', headers={'X-Admin-Token': 'test-token-secret'}
    )

    assert response.status_code == 200
    assert response.content == fake_dump
    assert response.headers['content-type'] == 'application/octet-stream'
    assert 'attachment' in response.headers['content-disposition']
    assert '.dump' in response.headers['content-disposition']


def test_export_fails_when_pg_dump_binary_missing(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch('app.api.routes.admin.shutil.which', return_value=None)
    response = client.get(
        '/api/admin/export', headers={'X-Admin-Token': 'test-token-secret'}
    )
    assert response.status_code == 500


def test_export_rejects_malformed_postgres_url(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('POSTGRES_URL', 'not-a-url')
    response = client.get(
        '/api/admin/export', headers={'X-Admin-Token': 'test-token-secret'}
    )
    assert response.status_code == 500


# ──────────────────────────────────────────────────────────────────────────
# Restore, input validation with mocked pg_restore
# ──────────────────────────────────────────────────────────────────────────


def test_restore_rejects_empty_upload(
    client: TestClient, mocker: MockerFixture
) -> None:
    mocker.patch(
        'app.api.routes.admin.shutil.which', return_value='/usr/bin/pg_restore'
    )
    response = client.post(
        '/api/admin/restore',
        headers={'X-Admin-Token': 'test-token-secret'},
        files={'file': ('empty.dump', b'', 'application/octet-stream')},
    )
    assert response.status_code == 400


def test_restore_rejects_invalid_dump_format(
    client: TestClient, mocker: MockerFixture
) -> None:
    """pg_restore -l fails on garbage input, the route must surface that as 400
    and never proceed to the destructive pg_restore --clean call."""
    list_proc = AsyncMock(spec=Process)
    list_proc.returncode = 1
    list_proc.communicate = AsyncMock(return_value=(b'', b'not a valid dump'))

    mocker.patch(
        'app.api.routes.admin.shutil.which', return_value='/usr/bin/pg_restore'
    )
    create_proc = mocker.patch(
        'app.api.routes.admin.asyncio.create_subprocess_exec',
        AsyncMock(return_value=list_proc),
    )

    response = client.post(
        '/api/admin/restore',
        headers={'X-Admin-Token': 'test-token-secret'},
        files={'file': ('garbage.dump', b'random bytes', 'application/octet-stream')},
    )

    assert response.status_code == 400
    # Critical safety property: only the validation call ran, the real restore
    # was never invoked.
    assert create_proc.call_count == 1


def test_restore_runs_pg_restore_on_valid_dump(
    client: TestClient, mocker: MockerFixture
) -> None:
    list_proc = AsyncMock(spec=Process)
    list_proc.returncode = 0
    list_proc.communicate = AsyncMock(return_value=(b'TOC entries', b''))

    restore_proc = AsyncMock(spec=Process)
    restore_proc.returncode = 0
    restore_proc.communicate = AsyncMock(return_value=(b'', b''))

    mocker.patch(
        'app.api.routes.admin.shutil.which', return_value='/usr/bin/pg_restore'
    )
    mocker.patch(
        'app.api.routes.admin.asyncio.create_subprocess_exec',
        AsyncMock(side_effect=[list_proc, restore_proc]),
    )

    response = client.post(
        '/api/admin/restore',
        headers={'X-Admin-Token': 'test-token-secret'},
        files={'file': ('valid.dump', b'PGDMP\x00...', 'application/octet-stream')},
    )

    assert response.status_code == 200
    assert response.json()['status'] == 'success'


def test_restore_surfaces_pg_restore_failure(
    client: TestClient, mocker: MockerFixture
) -> None:
    list_proc = AsyncMock(spec=Process)
    list_proc.returncode = 0
    list_proc.communicate = AsyncMock(return_value=(b'TOC', b''))

    restore_proc = AsyncMock(spec=Process)
    restore_proc.returncode = 1
    restore_proc.communicate = AsyncMock(return_value=(b'', b'connection refused'))

    mocker.patch(
        'app.api.routes.admin.shutil.which', return_value='/usr/bin/pg_restore'
    )
    mocker.patch(
        'app.api.routes.admin.asyncio.create_subprocess_exec',
        AsyncMock(side_effect=[list_proc, restore_proc]),
    )

    response = client.post(
        '/api/admin/restore',
        headers={'X-Admin-Token': 'test-token-secret'},
        files={'file': ('valid.dump', b'PGDMP\x00...', 'application/octet-stream')},
    )

    assert response.status_code == 500
    assert 'connection refused' in response.json()['detail']
