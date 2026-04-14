# Todo List

## Offline Functionality
-  [ ] Caching so desktop app feels snappy.
-  [ ] MinIO for local storage of media files, allowing users to access their media library even without an internet connection. This will involve setting up a local MinIO server and integrating it with the desktop client to manage media files effectively.

## User Management
- [ ] User Authentication: Implement a secure login system.
- [ ] User Profiles: Allow users to create and manage their profiles, including preferences and watch history.

## Desktop Client
- [ ] Graphics API Update: Ensure the video player is not solely tied to legacy OpenGL and uses the modern Qt 6 rendering methods (RHI). See documentation: https://doc.qt.io/qt-6/opengl-changes-qt6.html

## Deployment & Infrastructure
- [ ] CI/CD Pipeline: Set up a continuous integration and deployment pipeline to automate testing and deployment processes.
- [ ] Homelab Deployment: Deploy the application to a homelab environment, ensuring hardware acceleration is handled properly for each platform.
- [ ] Cross-Platform Packaging: Ensure the desktop app is cross-platform compatible (Windows, macOS, Linux) and can be easily installed by users via native installers.

## Extras
- [ ] Rating System: Implement a feature that allows users to rate movies and TV shows, and display average ratings on the frontend.

## General Maintenance
- [ ] Code Refactoring
- [ ] Architectural Improvements
- [ ] Documentation
- [ ] Testing
- [ ] Readme Update