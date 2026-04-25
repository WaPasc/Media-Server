import asyncio
import os
import shutil
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

router = APIRouter(prefix='/api/admin', tags=['admin'])


# Until real auth lands, gate admin endpoints behind a shared secret. Refuse
# entirely if ADMIN_TOKEN is unset - fail closed, never accidentally open.
def _require_admin(x_admin_token: str | None) -> None:
    expected = os.getenv('ADMIN_TOKEN')
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Admin endpoints disabled: ADMIN_TOKEN not configured',
        )
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid admin token'
        )


def _parse_postgres_url() -> dict:
    """Extract host/port/user/password/db from POSTGRES_URL.

    pg_dump and pg_restore don't understand SQLAlchemy-style URLs, and we want
    to pass the password via the PGPASSWORD env var rather than embed it in the
    process command line where it'd show up in `ps`.
    """
    url = os.getenv('POSTGRES_URL')
    if not url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='POSTGRES_URL not configured',
        )

    parsed = urlparse(url)
    if not parsed.hostname or not parsed.path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Malformed POSTGRES_URL',
        )

    return {
        'host': parsed.hostname,
        'port': str(parsed.port or 5432),
        'user': parsed.username or '',
        'password': parsed.password or '',
        'database': parsed.path.lstrip('/'),
    }


def _pg_env(creds: dict) -> dict:
    env = os.environ.copy()
    env['PGPASSWORD'] = creds['password']
    return env


def _require_binary(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'{name} binary not found on server',
        )
    return path


@router.get('/export')
async def export_database(x_admin_token: str | None = Header(default=None)):
    """Stream a pg_dump of the application database as a downloadable file.

    Uses custom format (-Fc), which is compressed and required by
    pg_restore --clean --if-exists.
    """
    _require_admin(x_admin_token)
    creds = _parse_postgres_url()
    pg_dump = _require_binary('pg_dump')

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    filename = f'streamservice-{timestamp}.dump'

    proc = await asyncio.create_subprocess_exec(
        pg_dump,
        '-h',
        creds['host'],
        '-p',
        creds['port'],
        '-U',
        creds['user'],
        '-d',
        creds['database'],
        '-Fc',
        '--no-owner',
        '--no-privileges',
        env=_pg_env(creds),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def stream():
        # Stream stdout in chunks so we don't buffer the whole dump in RAM.
        try:
            assert proc.stdout is not None
            while True:
                chunk = await proc.stdout.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
            await proc.wait()
            if proc.returncode != 0:
                stderr = b''
                if proc.stderr is not None:
                    stderr = await proc.stderr.read()
                # The response body has already started - best we can do is log
                # to stderr server-side. The client will see a truncated dump,
                # which pg_restore will reject.
                print(
                    f'pg_dump failed (rc={proc.returncode}): {stderr.decode(errors="replace")}'
                )
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

    return StreamingResponse(
        stream(),
        media_type='application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@router.post('/restore')
async def restore_database(
    file: UploadFile,
    x_admin_token: str | None = Header(default=None),
):
    """Restore the application database from an uploaded pg_dump custom-format file.

    Validates the uploaded file with `pg_restore -l` before applying it, so a
    bad/empty upload can't drop the live schema.
    """
    _require_admin(x_admin_token)
    creds = _parse_postgres_url()
    pg_restore = _require_binary('pg_restore')

    body = await file.read()
    if not body:
        raise HTTPException(status_code=400, detail='Empty file')

    # Validate: -l prints the dump's table of contents without touching the DB.
    # If the file isn't a valid custom-format dump, this exits non-zero before
    # we go anywhere near --clean.
    list_proc = await asyncio.create_subprocess_exec(
        pg_restore,
        '-l',
        env=_pg_env(creds),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, list_err = await list_proc.communicate(
        body
    )  # Communicate writes body to stdin and waits for process to exit
    if list_proc.returncode != 0:
        raise HTTPException(
            status_code=400,
            detail=f'Invalid dump file: {list_err.decode(errors="replace").strip()}',
        )

    restore_proc = await asyncio.create_subprocess_exec(
        pg_restore,
        '-h',
        creds['host'],
        '-p',
        creds['port'],
        '-U',
        creds['user'],
        '-d',
        creds['database'],
        '--clean',
        '--if-exists',
        '--no-owner',
        '--no-privileges',
        env=_pg_env(creds),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, restore_err = await restore_proc.communicate(body)
    if restore_proc.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f'pg_restore failed: {restore_err.decode(errors="replace").strip()}',
        )

    return {'status': 'success', 'message': 'Database restored'}
