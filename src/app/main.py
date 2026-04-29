import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, history, movies, progress, scanner, shows, stream
from app.core.s3 import s3_client
from app.services.imdb_dataset_service import refresh_if_stale as imdb_refresh_if_stale
from app.services.tmdb_client import TMDBClient
from app.utils.s3_utils import apply_public_read_policy, ensure_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tmdb_client = await TMDBClient.create(timeout=10.0)

    if s3_client.images_bucket:
        await ensure_bucket_exists(s3_client.images_bucket)
        await apply_public_read_policy(s3_client.images_bucket)

    # Fire-and-forget: the dataset ingest takes a few seconds and we don't
    # want to block readiness on it. Hold a reference so the task isn't
    # garbage-collected before it finishes.
    app.state.imdb_refresh_task = asyncio.create_task(imdb_refresh_if_stale())

    try:
        yield
    finally:
        await app.state.tmdb_client.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],  # TODO: Change to frontend URL
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(shows.router)
app.include_router(movies.router)
app.include_router(stream.router)
app.include_router(progress.router)
app.include_router(scanner.router)
app.include_router(history.router)
app.include_router(admin.router)


if __name__ == '__main__':
    config = uvicorn.Config(
        app='app.main:app', host='0.0.0.0', port=8000, log_level='info'
    )
    server = uvicorn.Server(config)
    server.run()
