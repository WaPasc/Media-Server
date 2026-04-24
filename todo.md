# Todo List

## Offline Functionality
-  [ ] Caching so desktop app feels snappy.

## User Management
- [ ] User Authentication: Implement a secure login system.
- [ ] User Profiles: Allow users to create and manage their profiles, including preferences and watch history.

## Desktop Client
- [ ] Graphics API Update: Ensure the video player is not solely tied to legacy OpenGL and uses the modern Qt 6 rendering methods (RHI). See documentation: https://doc.qt.io/qt-6/opengl-changes-qt6.html

## Web Application
- [ ] Update the web application to use all the new features and improvements from the backend, ensuring a seamless user experience across both platforms.

## Deployment & Infrastructure
- [ ] CI/CD Pipeline: Set up a continuous integration and deployment pipeline to automate testing and deployment processes.
- [ ] Homelab Deployment: Deploy the application to a homelab environment, ensuring hardware acceleration is handled properly for each platform.
- [ ] Cross-Platform Packaging: Ensure the desktop app is cross-platform compatible (Windows, macOS, Linux) and can be easily installed by users via native installers.

## Extras
- [ ] Rating System: Implement a feature that allows users to rate movies and TV shows, and display average ratings on the frontend.

## Testing

### No infrastructure needed (safe for CI)
- [ ] **TMDB client - offline resilience**: verify `_load_configuration` catches `ConnectError`/`TimeoutException`, `config` stays `None`, and image URL methods return `None` instead of raising
- [ ] **TMDB client - lazy retry**: verify `ensure_configured()` loads config successfully on a second attempt after an initial failure


### Needs MinIO (already in CI)
- [ ] **MinIO service - startup bucket creation**: verify `ensure_bucket_exists` + `apply_public_read_policy` are called correctly on lifespan startup

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