# Personal Media Server & Client

A self-hosted media streaming platform designed to automatically organize, manage, and stream local video libraries.

This project consists of a asynchronous backend built with **FastAPI** and **SQLAlchemy 2.0**, paired with a custom desktop client engineered in **Qt/QML**. It features automated metadata tagging, stateful watch progress tracking, and a background scanner (trigger manually).

---

## Key Features

  * **Automated Metadata Ingestion:** On triggering a background worker scans local storage directories, parses file names, and interacts with the TMDB API to fetch metadata (posters, backdrops, episode descriptions, and release years).
  * **"Soft Delete" Architecture:** Employs a robust background availability scanner. If a physical hard drive is disconnected, the system safely flags files as `unavailable` rather than deleting them. This ensures zero data loss of user watch history and seamlessly restores access when the drive is reconnected.
  * **Stateful Playback & Tracking:** Features a "Continue Watching" system that saves watch progress per user, per file. Seamlessly resumes playback across sessions.
  * **Custom Desktop UI:** Engineered a custom Qt/QML desktop application featuring a C++ `libmpv` integration. This architecture ensures efficient, GPU-accelerated video decoding and rendering, allowing for smooth UI interactions even during playback.
  * **Direct Streaming:** The backend serves high-bitrate media directly to the client via asynchronous byte-range streaming endpoints.

---

## Tech Stack

**Backend (RESTful API & Workers)**

  * **Language:** Python 3.10+
  * **Framework:** FastAPI
  * **Database:** PostgreSQL (via Async SQLAlchemy 2.0)
  * **Migrations:** Alembic
  * **Integrations:** TMDB (The Movie Database) API

**Frontend (Desktop Client)**

  * **Language:** QML / TypeScript / C++
  * **Framework:** Qt 6 (Qt Quick, Qt Quick Controls)
  * **Video Playback:** Native Qt Multimedia integration

---

## Getting Started

### Prerequisites

  * Python 3.10+
  * Qt 6.5+
  * A TMDB API Key

### Backend Setup

1.  Clone the repository and navigate to the backend directory.
2.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
3.  Copy `.env.example` to `.env` and add your TMDB API Key and database URL.
4.  Run the database migrations to build the schema:
    ```bash
    alembic upgrade head
    ```
5.  Start the API server:
    ```bash
    python src/app/main.py
    ```

### Frontend Setup

1.  Open the `CMakeLists.txt` file in **Qt Creator**.
2.  Build and run the project.
3.  In the client settings, point the server URL to `http://127.0.0.1:8000`.

## Architecture Overview

```text
├── backend/
    ├── alembic/              # Database migration scripts
    ├── app/
        ├── api/              # FastAPI route controllers
        ├── core/             # Application configuration and utilities
        ├── mappers/          # Functions to map TMDB API responses to internal models
        ├── models/           # SQLAlchemy 2.0 declarative models
        ├── schemas/          # Pydantic validation schemas
        ├── utils/            # Utility functions and helpers
        └── services/         # Core business logic & background scanners
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/WaPasc/Media-Server/blob/main/LICENSE) file for details.
