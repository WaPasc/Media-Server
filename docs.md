
## Database Migrations
```bash
python -m alembic revision --autogenerate -m "Initial migration"
python -m alembic upgrade head
```

## Python
This command will install the package in editable mode, allowing you to make changes to the code and have them reflected without needing to reinstall the package.
```bash
pip install -e .
```


## Docker commands
```
docker compose up
```

## IMDb ratings dataset

Episode and movie ratings come from IMDb's free non-commercial dataset
(https://datasets.imdbws.com/title.ratings.tsv.gz). It's downloaded on
backend startup if missing or older than 7 days, and ingested into the
`imdb_ratings` table (~1.66M rows, ~50 MB).

**Storage**: `./app_data/imdb/title.ratings.tsv.gz` on the host, mounted
into the container at `/app/data/imdb/` via the existing
`./app_data:/app/data` bind mount in `docker-compose.yml`. No new env
vars are required.

**Manual refresh** (forces a download regardless of file age):
```bash
curl -X POST http://localhost:8000/api/admin/refresh-imdb-ratings \
  -H "X-Admin-Token: $ADMIN_TOKEN"
```

**Permissions**: the container's `appuser` is uid 1000. If
`./app_data/` ends up owned by root (e.g. Docker autocreated it before
the host directory existed), the dataset download fails with
`Permission denied`. The repo ships `app_data/imdb/.gitkeep` so the
directory exists with the cloning user's ownership before Docker ever
touches it. If you still hit it:
```bash
sudo chown -R 1000:1000 app_data/
```

**Why .gitkeep is safe to commit**: `.gitignore` is layered so only
`.gitkeep` is tracked, the dataset file (`title.ratings.tsv.gz`) and
the temp file used during atomic download (`*.tmp`) stay ignored.