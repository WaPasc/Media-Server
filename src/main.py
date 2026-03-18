import mimetypes
import os
from contextlib import asynccontextmanager

import aiofiles
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from database import get_db
from db_models import Episode, MediaFile, Movie, Season, TVShow
from tmdb_client import TMDBClient

CHUNK_SIZE = 1024 * 1024 * 2


content_types = {
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.mkv': 'video/x-matroska',
}


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


@app.get('/api/movies')
async def get_movies(request: Request, db: AsyncSession = Depends(get_db)):
    """Fetches all scanned movies and returns them with full poster URLs"""

    stmt = select(Movie).options(selectinload(Movie.files))
    result = await db.execute(stmt)
    movies = result.scalars().all()

    # Retrieve TMDB client from app state
    tmdb_client: TMDBClient = request.app.state.tmdb_client

    # Format response using a list comprehension
    return [
        {
            'id': m.id,
            'title': m.title,
            'year': m.year,
            'overview': m.overview,
            'poster_url': tmdb_client.get_poster_url(m.poster_path)
            if m.poster_path
            else None,
            'backdrop_url': tmdb_client.get_backdrop_url(m.backdrop_path)
            if m.backdrop_path
            else None,
            'file_id': m.files[0].id if m.files else None,
        }
        for m in movies
    ]


@app.get('/api/shows')
async def get_shows(request: Request, db: AsyncSession = Depends(get_db)):
    """Fetches all scanned TV shows and returns them with full poster URLs"""
    stmt = select(TVShow)  # Removed the invalid selectinload
    result = await db.execute(stmt)
    shows = result.scalars().all()

    tmbd_client: TMDBClient = request.app.state.tmdb_client

    show_list = []
    for s in shows:
        show_list.append(
            {
                'id': s.id,
                'title': s.title,
                'year': s.year,
                'overview': s.overview,
                'poster_url': tmbd_client.get_poster_url(s.poster_path)
                if s.poster_path
                else None,
                'backdrop_url': tmbd_client.get_backdrop_url(s.backdrop_path)
                if s.backdrop_path
                else None,
            }
        )

    return show_list


@app.get('/api/show/{show_id}')
async def get_show_details(
    show_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    """Fetches detailed info for a specific TV show, including seasons and episodes"""

    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id)
        .options(
            selectinload(TVShow.seasons)
            .selectinload(Season.episodes)
            .selectinload(Episode.files)
        )
    )
    result = await db.execute(stmt)
    show = result.scalars().first()

    if not show:
        raise HTTPException(status_code=404, detail='TV show not found')

    tmdb_client: TMDBClient = request.app.state.tmdb_client

    return {
        'id': show.id,
        'title': show.title,
        'year': show.year,
        'overview': show.overview,
        'poster_url': tmdb_client.get_poster_url(show.poster_path)
        if show.poster_path
        else None,
        'backdrop_url': tmdb_client.get_backdrop_url(show.backdrop_path)
        if show.backdrop_path
        else None,
        'seasons': [
            {
                'season_number': season.season_number,
                'episodes': [
                    {
                        'episode_number': ep.episode_number,
                        'title': ep.title,
                        'overview': ep.overview,
                        'file_id': ep.files[0].id if ep.files else None,
                    }
                    for ep in season.episodes
                ],
            }
            for season in show.seasons
        ],
    }


@app.get('/api/stream/{file_id}')
async def stream_video(
    file_id: int, range: str = Header(None), db: AsyncSession = Depends(get_db)
):
    """Streams a video file in chunks using HTTP Range Requests."""

    # Look up the file path in the database
    stmt = select(MediaFile).where(MediaFile.id == file_id)
    result = await db.execute(stmt)
    media_file = result.scalars().first()

    if not media_file or not os.path.exists(media_file.file_path):
        raise HTTPException(status_code=404, detail='Media file not found on disk')

    file_path = media_file.file_path
    file_size = os.path.getsize(file_path)

    # Parse the Range header (e.g., "bytes=0-")
    start = 0
    end = file_size - 1

    if range:
        range_str = range.replace('bytes=', '')
        parts = range_str.split('-')
        start = int(parts[0]) if parts[0] else 0
        # Sometimes the browser requests a specific end byte, sometimes it just wants "everything after start"
        end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

    # Validate the range
    if start >= file_size:
        raise HTTPException(status_code=416, detail='Requested Range Not Satisfiable')

    # Limit the chunk size so we don't overload the server's RAM
    end = min(start + CHUNK_SIZE - 1, end)
    content_length = end - start + 1

    # Create a generator to stream the file chunk from disk
    async def file_iterator(path, offset, bytes_to_read):
        async with aiofiles.open(path, mode='rb') as f:
            await f.seek(offset)
            bytes_left = bytes_to_read
            while bytes_left > 0:
                # Read in smaller 64KB chunks inside the generator for memory efficiency
                read_size = min(65536, bytes_left)
                data = await f.read(read_size)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    # Build the headers required for a 206 Partial Content response
    # Simple mime-type guess based on extension
    content_type, _ = mimetypes.guess_type(file_path)

    # Fallback if system doesn't recognize the extension
    if not content_type:
        content_type = 'application/octect-stream'

    headers = {
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes',
        'Content-Length': str(content_length),
        'Content-Type': content_type,
    }

    # Return the chunk
    return StreamingResponse(
        file_iterator(file_path, start, content_length),
        status_code=206,
        headers=headers,
    )


if __name__ == '__main__':
    config = uvicorn.Config(app=app, host='127.0.0.1', port=8000, log_level='info')
    server = uvicorn.Server(config)
    server.run()
