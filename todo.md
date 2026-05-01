# Todo List

## User Management
- [ ] User Authentication: Implement a secure login system.
- [ ] User Profiles: Allow users to create and manage their profiles, including preferences and watch history.
- [ ] Multi-user support: per-user history, progress, ratings.
- [ ] Migration path: on first multi-user rollout, assign all existing accumulated data to current owner as the first user.
- [ ] Per-user data export/import: a user can export their own progress/history/ratings and re-import after cloning the repo elsewhere.

## Data Lifecycle & Backup
- [ ] Restore-on-readd: when a previously removed show/movie reappears, automatically rebind history (watched episodes, progress, ratings, metadata). *(Foundation now in place — WatchProgress anchors on Movie/Episode, so re-adding a file naturally rebinds. Still need: scanner-side reconciliation pass + UI affordance.)*

## UI / Metadata
- [ ] Show cast and crew on detail screens.

## Web Application
- [ ] Update the web application to use all the new features and improvements from the backend, ensuring a seamless user experience across both platforms.

## Deployment & Infrastructure
- [ ] CI/CD Pipeline: Set up a continuous integration and deployment pipeline to automate testing and deployment processes.
- [ ] Homelab Deployment: Deploy the application to a homelab environment, ensuring hardware acceleration is handled properly for each platform.
- [ ] Cross-Platform Packaging: Ensure the desktop app is cross-platform compatible (Windows, macOS, Linux) and can be easily installed by users via native installers.

## Extras
- [ ] Rating System: per-user ratings on movies/shows/episodes for personal recall.
- [ ] Discovery System: recommendation engine using TMDB (similar/recommendations/discover) driven by watch history, ratings, and a "more like this" entry point per title.

## Testing

### Needs Postgres service container in CI
- [ ] **Movie/show routes - happy path**: `GET /api/movies`, `GET /api/movie/{id}`, `GET /api/shows`, `GET /api/show/{id}` return correct shape with seeded data
- [ ] **Streaming route - range requests**: verify `Content-Range` header and partial content (206) response for MP4 files
- [ ] **Progress route**: verify watch position is saved and returned correctly per user
- [ ] **History route**: verify only started/completed items are returned
- [ ] **Scanner service - DB writes**: verify a scan of a temp directory with fake filenames creates the correct Movie/TVShow/Episode/MediaFile records
- [ ] **Soft delete**: verify that removing a file from disk marks `is_available=False` without deleting watch progress

### End-to-end (manual / homelab only)
- [ ] Full scan → metadata fetch → stream flow with a real media file
- [ ] FFmpeg transcoding path (MKV → H.264) produces playable output
- [ ] Desktop client connects and plays a stream end-to-end

## General Maintenance
- [ ] Code Refactoring
- [ ] Architectural Improvements
- [ ] Testing
- [ ] Documentation
- [ ] Readme Update