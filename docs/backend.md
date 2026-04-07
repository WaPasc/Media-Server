# Backend Documentation

This document explains how the backend is structured, how data flows through it, and how to use the API quickly.

## 1) What This Backend Does

The backend is a FastAPI service that:

- indexes movie and TV files from configured filesystem directories
- enriches content metadata with TMDB
- tracks playback progress and watch history
- streams files to clients, including optional on-the-fly MKV transcoding
- marks missing files as unavailable instead of deleting records

Main stack:

- FastAPI
- SQLAlchemy 2.0 async
- PostgreSQL
- Alembic
- httpx for TMDB calls
- ffprobe + ffmpeg for media inspection and transcoding

## 2) High-Level Architecture

Layered structure:

- API routes: request/response wiring and validation
- services: business logic and database querying
- models: SQLAlchemy entities and relationships
- schemas: API contracts (Pydantic)
- mappers/utils: response composition and helper logic

Flow summary:

1. Client calls route.
2. Route resolves dependencies (database session, TMDB client).
3. Service queries/updates DB and may call TMDB/filesystem.
4. Schema/mapper builds stable response payload.

## 3) Runtime Lifecycle

- App startup creates a shared TMDB client in FastAPI lifespan state.
- DB sessions are provided per request through dependency injection.
- TMDB client is closed on app shutdown.
- CORS is currently fully open (all origins/methods/headers).

## 4) Directory Map (Backend)

- src/app/main.py: app creation, middleware, route registration, lifespan
- src/app/api/routes/: route modules
- src/app/api/dependencies.py: get_db + get_tmdb_client
- src/app/services/: core use cases (scan, stream, history, progress, availability)
- src/app/models/: database models
- src/app/schemas/: request/response schemas
- src/app/mappers/: view model mapping
- src/alembic/: migrations

## 5) Configuration

Required environment variables:

- POSTGRES_URL: base DB URL (converted internally to async SQLAlchemy URL)
- TMDB_READ_ACCESS: TMDB Bearer token used by TMDBClient

Notes:

- If POSTGRES_URL is missing, backend startup fails fast.
- If TMDB_READ_ACCESS is missing, TMDB client initialization fails.

## 6) Data Model Essentials

Core entities:

- Movie
- TVShow
- Season
- Episode
- MediaFile
- WatchProgress
- UserShowProgress
- ScanDirectory

Important constraints and behavior:

- MediaFile must belong to either a movie or an episode (never both).
- WatchProgress has a unique (user_id, media_file_id) constraint (upsert semantics).
- Soft availability model:
	- MediaFile has is_available.
	- Movie/Episode availability is rolled up from child files.
- Deletions on parent media cascade to child entities.

## 7) Scanning and Metadata Pipeline

### 7.1 Directory-driven scanning

- Scanner reads all ScanDirectory rows.
- For each directory:
	- movies -> movie scanner
	- shows -> TV scanner
- last_scanned is updated after each directory run.

### 7.2 Local metadata extraction

- Filename parsing via PTN (title, season, episode, year).
- Technical probing via ffprobe (duration, codec, resolution).

### 7.3 TMDB enrichment

- Movie and TV lookups are performed via TMDB API.
- TV matching strategy:
	- strict title+year
	- fallback title only
	- final fallback to top TMDB result
- Image paths are converted to full URLs with TMDB configuration loaded at startup.

### 7.4 Idempotency and safety

- Existing absolute file paths are skipped during scan.
- Per-file failures rollback safely without breaking whole scan loop.

## 8) Availability Scan (Soft Delete Strategy)

Availability scan checks if files still exist on disk.

- If a file disappears: MediaFile.is_available = false
- If a file returns: MediaFile.is_available = true
- Parent Movie/Episode availability is recalculated
- Data is preserved (no hard delete)

This protects progress/history when drives are temporarily disconnected.

## 9) Streaming Behavior

Endpoint uses two paths:

- Native file serving:
	- MP4/WebM and other direct-play paths
	- uses FileResponse, supports HTTP range requests
- Live transcoding:
	- MKV files default to ffmpeg transcoding to fragmented MP4
	- set direct_play=true to bypass transcoding when client can handle source

If file is not found in DB or missing on disk, response is 404.

## 10) Progress and History Logic

Progress:

- POST /api/progress upserts watch progress.
- Completion is determined by threshold 95% of total duration.
- has_ever_completed remains true once a file has been completed.

Continue Watching:

- GET /api/continue-watching returns non-completed items with stopped_at > 0.
- ordered by most recently updated.
- payload is a union of:
	- movie item
	- episode item

History:

- GET /api/history returns items where has_ever_completed is true.
- ordered by updated_at descending.

Current MVP assumption:

- user_id is hardcoded to 1 in progress/history routes.
- auth/multi-user support is not implemented yet.

## 11) API Reference

All routes are currently mounted under /api except scanner routes (/api/scanner/*).

### 11.1 Shows

GET /api/shows

- query: skip (default 0), limit (default 50)
- returns: list of show cards with image URLs

GET /api/show/{show_id}

- returns: detailed show object with nested seasons and episodes
- episode payload includes file_id when an available file exists
- 404 if show not found

### 11.2 Movies

GET /api/movies

- query: skip (default 0), limit (default 50)
- returns: list of movies, with chosen file_id if playable file is available

GET /api/movie/{movie_id}

- returns: detailed movie payload
- 404 if movie not found

### 11.3 Streaming

GET /api/stream/{file_id}

- query: direct_play (default false)
- behavior:
	- MKV + direct_play=false -> ffmpeg transcoding stream
	- otherwise -> native file response
- 404 if media file path missing/unavailable

### 11.4 Progress

POST /api/progress

- body:
	- file_id: int
	- current_time: float
	- total_duration: float
- returns:
	- status
	- stopped_at
	- is_completed

GET /api/progress/{file_id}

- returns stopped_at
- if no unfinished progress exists, returns stopped_at = 0.0

GET /api/continue-watching

- returns mixed list of movie/episode continue-watching items

### 11.5 History

GET /api/history

- returns fully completed watch items (movie or episode typed payload)

### 11.6 Scanner

GET /api/scanner/directories

- list configured scan directories

POST /api/scanner/directories

- body:
	- path: string
	- media_type: movies | shows
- returns created directory
- 400 if media_type invalid

DELETE /api/scanner/directories/{directory_id}

- returns 204 on success
- 404 if directory not found

POST /api/scanner/scan

- triggers full scan as background task
- returns immediate confirmation message

POST /api/scanner/scan-availability

- triggers availability scan in background
- returns status message

## 12) Error Patterns and Status Codes

Common status codes:

- 200: successful read/update
- 204: successful delete (no body)
- 400: validation/business rule violation (example: invalid media_type)
- 404: missing resource (movie/show/file/directory)

Unhandled internal errors from dependencies (DB/TMDB/ffmpeg/filesystem) surface as 5xx unless caught.

## 13) Running the Backend Locally

Typical flow:

1. Ensure PostgreSQL is running and POSTGRES_URL is valid.
2. Set TMDB_READ_ACCESS.
3. Run migrations: alembic upgrade head.
4. Start app: python src/app/main.py.
5. Add scan directories via scanner API.
6. Trigger /api/scanner/scan.
