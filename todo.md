# Todo List

## Offline Functionality
-  [ ] Caching so desktop app feels snappy.

## DevOps
- [ ] Make sure the bucket is created on startup if it doesn't exist, to avoid issues with missing buckets when deploying to new environments. Also the anonymous user should be created if it doesn't exist, to avoid issues with permissions when deploying to new environments.

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

## General Maintenance
- [ ] Code Refactoring
- [ ] Architectural Improvements
- [ ] Documentation
- [ ] Testing
- [ ] Readme Update