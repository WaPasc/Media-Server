# Todo List

## Scanner
- [ ] Improve Scanner for TV Shows: Now it's not accurate

## Continue Watching
- [ ] Progress Bar: Implement a progress bar to visually indicate how much of the video has been watched.
- [ ] Button to Continue: Add a button that allows users to easily continue watching from where they left off.
- [ ] Next Episode Auto-Queue ("Up Next"): Implement logic so that if a user finishes Season 1 Episode 1, the system automatically places Season 1 Episode 2 in their "Continue Watching" row.

## Frontend & Player Experience
- [ ] Hero Banner: Add a large featured media banner to the top of the main library screens.
- [ ] Volume Control: Implement a volume control feature in the video player for better user experience.
- [ ] Audio Track Selection: Add a button in the video player to cycle through audio tracks (crucial for anime or dual-audio MKV files).
- [ ] Auto-Play Next Episode: Implement a countdown at the end of a TV episode that automatically launches the next file.
- [ ] Pagination / Infinite Scroll: Add lazy-loading to the frontend to handle rendering thousands of movies efficiently without overloading the DOM/QML.
- [ ] Metadata Refresh: Add a button in the UI to force an update from TMDB in case a poster changes or new cast info is added.

## Library & Media Management
- [ ] Soft Delete: Update the database models so that deleting a file flips an `is_available = False` flag instead of erasing the row entirely (ensures watch history and ratings are preserved).
- [ ] Directory Rescanner: Implement a feature that allows users to rescan their media directories to update the library with any new or removed files.
- [ ] Add Manual Path: Add a button in the desktop app to add a manual file path to the library.
- [ ] Watch History System: Create a system to track which videos have been watched.
- [ ] Media Engine Upgrade: Remove basic scripting and replace with a more robust solution for handling media files, such as a dedicated media management library or service.

## User Management
- [ ] User Authentication: Implement a secure login system.
- [ ] User Profiles: Allow users to create and manage their profiles, including preferences and watch history.
- [ ] User Watch History: Implement a feature to track and display the watch history for each user, allowing them to easily find and rewatch previously viewed content.

## Desktop Client
- [ ] Graphics API Update: Ensure the video player is not solely tied to legacy OpenGL and uses the modern Qt 6 rendering methods (RHI). See documentation: https://doc.qt.io/qt-6/opengl-changes-qt6.html

## Deployment & Infrastructure
- [ ] Dockerization: Create a Dockerfile to containerize the application for easier deployment and scalability.
- [ ] CI/CD Pipeline: Set up a continuous integration and deployment pipeline to automate testing and deployment processes.
- [ ] Homelab Deployment: Deploy the application to a homelab environment, ensuring hardware acceleration is handled properly for each platform.
- [ ] Cross-Platform Packaging: Ensure the desktop app is cross-platform compatible (Windows, macOS, Linux) and can be easily installed by users via native installers.

## Extras
- [ ] Rating System: Implement a feature that allows users to rate movies and TV shows, and display average ratings on the frontend.
- [ ] External Subtitle Support: Add support for external subtitle files (e.g., .srt) and ensure they are properly synced with the video playback.

## General Maintenance
- [ ] Code Refactoring
- [ ] Architectural Improvements
- [ ] Documentation
- [ ] Testing
- [ ] Readme Update