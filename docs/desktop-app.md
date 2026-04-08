# Desktop App Documentation (QML Client)

This is the current architecture and behavior of the Qt desktop client under desktop/MediaServerClient.

## 1) What It Does

The desktop app:

- Browses movies and shows from the backend
- Opens movie/show detail pages
- Plays media via embedded mpv
- Sends watch progress updates
- Shows continue-watching and history lists
- Manages scanner directories from settings

Stack:

- Qt 6 Quick / QML for UI
- JavaScript (XMLHttpRequest) for HTTP calls
- C++ mpv bridge (QQuickFramebufferObject)
- CMake build

## 2) Runtime Architecture

The app is a single Window state router in Main.qml.

State:

- currentScreen: library | movieDetail | showDetail | player | settings | history
- playerReturnScreen: where to return after leaving player

Flow:

1. main.cpp sets OpenGL backend and LC_NUMERIC=C
2. MpvVideo (from MpvItem) is registered into QML module MediaServerClient 1.0
3. Main.qml switches visible screens and forwards play/navigation signals

## 3) Routing Model

Main.qml keeps all major screens mounted and toggles visibility.

Primary transitions:

- Library -> MovieDetail / ShowDetail
- Library / MovieDetail / ShowDetail / History -> Player
- Player -> playerReturnScreen
- Library -> Settings / History

## 4) Implemented Shortcuts (Current)

Global shortcuts in Main.qml:

- F: toggle app fullscreen
- Esc: force windowed mode (showNormal) and focus library item

Player shortcuts in PlayerScreen.qml (when player has focus):

- Space: play/pause
- Left/Right:
  - key release without hold-repeat: seek -/+ 5s
  - hold with auto-repeat: repeated seek -/+ 15s (timer-driven)
- Up/Down: volume +/- 5
- M: toggle mute
- Double click/tap on video: toggle fullscreen

Player control bar actions:

- Back (stops playback, sends final progress update)
- Play/pause
- Seek slider (absolute seek)
- Volume slider and mute
- Cycle audio track
- Cycle subtitles
- Subtitle button right-click: open file picker and load external subtitle
- Fullscreen toggle button

## 5) Screen Responsibilities

LibraryScreen.qml:

- Loads movies/shows with pagination (skip/limit)
- Client-side search on loaded dataset
- Continue Watching row
- Emits selection and resume-to-player signals

MovieDetailScreen.qml:

- Loads movie details by movieId
- Emits moviePlay only when file is playable

ShowDetailScreen.qml:

- Loads show details with seasons/episodes
- Season switching and episode grid
- Computes next playable unwatched episode
- Marks unavailable episodes and blocks play for missing files

PlayerScreen.qml:

- Hosts MpvVideo
- Handles keyboard/mouse playback interactions
- Pulls resume position from /api/progress/{fileId}
- Sends progress every 5s while visible and playing
- Sends final progress on stop/back

HistoryScreen.qml:

- Loads /api/history
- Normalizes movie/episode entries for a shared landscape card model
- Emits play requests

SettingsScreen.qml:

- Lists scanner directories
- Adds/removes directories
- Triggers full scan

## 6) Networking Layer

NetworkManager.js exposes:

- get(endpoint)
- post(endpoint, body)
- del(endpoint)

Current behavior:

- BASE_URL is hardcoded to http://127.0.0.1:8000
- JSON parsing and HTTP error normalization are centralized
- No auth header injection yet

## 7) Backend Endpoints Used

Library/detail:

- GET /api/movies
- GET /api/movie/{movieId}
- GET /api/shows
- GET /api/show/{showId}

Playback/progress:

- GET /api/stream/{fileId}?direct_play=true
- GET /api/progress/{fileId}
- POST /api/progress

Personalized:

- GET /api/continue-watching
- GET /api/history

Scanner:

- GET /api/scanner/directories
- POST /api/scanner/directories
- DELETE /api/scanner/directories/{directoryId}
- POST /api/scanner/scan

## 8) mpv Bridge Notes

MpvItem (C++) wraps libmpv and renders through a Qt framebuffer object.

Key points:

- mpv options include vo=libmpv and hwdec=auto
- OpenGL proc addresses are provided from Qt context
- Wakeup callback is forwarded safely to GUI thread
- QML receives time and duration updates
- QML can call command(params) and setProperty(name, value)

