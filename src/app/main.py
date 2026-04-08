from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import history, movies, progress, scanner, shows, stream
from app.services.tmdb_client import TMDBClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.tmdb_client = await TMDBClient.create(timeout=10.0)
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


if __name__ == '__main__':
    config = uvicorn.Config(
        app='app.main:app', host='0.0.0.0', port=8000, log_level='info'
    )
    server = uvicorn.Server(config)
    server.run()
