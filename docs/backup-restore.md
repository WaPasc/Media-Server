# Database Backup & Restore

This is the safety net for the library: a way to dump the entire application
database to a single file and put it back later. Use it before risky
operations, before disk migrations, and on a regular cadence as protection
against disk failure.

## What's in the dump (and what isn't)

**Included** - everything in PostgreSQL: scanned movies, shows, episodes,
media-file records, watch progress, history, scan-directory config, alembic
version. The dump is in PostgreSQL's custom format (`pg_dump -Fc`), which is
compressed and required by `pg_restore --clean`.

**Not included** - MinIO assets (poster/backdrop images). Those can be
re-fetched from TMDB by re-running a scan, so they're left out to keep the
dump small and the restore fast. You only need to rerun the scanner once
after a full disk wipe restore.

## One-time setup

1. **Set `ADMIN_TOKEN` in `.env`.** Until real auth lands, both endpoints are
   gated by a shared secret. Generate one (`openssl rand -hex 32`) and put it
   in `.env`. If `ADMIN_TOKEN` is unset the endpoints return 503, fail
   closed by design.

2. **Rebuild the backend container.** The runtime image now ships
   `postgresql-client-17` so `pg_dump` and `pg_restore` are available inside
   the FastAPI container. After pulling these changes:

   ```bash
   docker compose up -d --build ms-backend
   ```

   Skip this and the first export call returns `500: pg_dump binary not found`.

## Exporting

`GET /api/admin/export` streams a `pg_dump` of the database as a downloadable
file named `streamservice-YYYYMMDD-HHMMSS.dump`.

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     http://localhost:8000/api/admin/export \
     -o "streamservice-$(date +%Y%m%d-%H%M%S).dump"
```

Move the resulting `.dump` file somewhere safe, external drive, cloud sync
folder, NAS, whatever you have. The dump is binary and compressed; don't
edit it.

## Restoring

`POST /api/admin/restore` accepts a previously exported `.dump` and applies
it with `pg_restore --clean --if-exists`. Existing tables are dropped and
recreated from the dump.

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
     -F "file=@streamservice-20260425-180000.dump" \
     http://localhost:8000/api/admin/restore
```

The route validates the upload with `pg_restore -l` before touching the
database, a corrupt or non-dump file is rejected with HTTP 400 and the live
schema is left alone.

After restore, the container's startup `alembic upgrade head` will fast-
forward the schema if the running code is newer than the dump. Restoring an
older dump into a newer codebase is supported; the reverse (newer dump,
older code) is not, older code can't run migrations it doesn't know about.

## What can go wrong

- **`pg_dump` version mismatch.** `pg_dump 14` cannot dump from a Postgres
  17 server. The runtime image pins client 17, but if you ever run the route
  outside the container make sure your host's `pg_dump --version` matches
  the server. Same applies to `pg_restore`.
- **Restore on a busy database.** `pg_restore --clean` drops tables; any
  open connections holding row locks will block it. Stop the application
  side of `docker compose` (just keep the database up) before restoring a
  large dump if you see hangs.
- **Wrong target database.** The route always restores into whatever
  `POSTGRES_URL` points at, there's no second safety prompt. Read the env
  before you fire the curl.

## Operational habits

This tool is the manual MVP. There's no scheduling, no rotation, no offsite
sync. Until those land:

- Take a fresh dump before adding/removing scan directories or running
  destructive maintenance.
- Take periodic dumps (weekly is plenty for a personal library) and store
  them on a different physical disk from the one running Postgres.
- Keep the last 2–3 dumps, not just the latest, the most recent dump can
  itself be corrupt.

## Testing

The route is covered by two test files:

- `tests/test_admin_export.py`, unit tests with `pg_dump`/`pg_restore`
  mocked. Never touches a real database. Runs by default in CI and via
  `scripts/test-unit.sh`.
- `tests/test_admin_restore_integration.py`, end-to-end round-trip test
  (seed → export → wipe → restore → verify). Skipped unless
  `TEST_POSTGRES_URL` is set, so it never accidentally hits your real
  `mediadb`. Run locally with `scripts/test-integration.sh` (creates and
  drops a uniquely-named throwaway database for each invocation). Also
  runs in CI against a Postgres 17 service container.
