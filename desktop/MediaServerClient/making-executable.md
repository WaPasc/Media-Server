# Steps to create the executable

## Linux

### 1. Deployment
Move to build directory
```bash
mkdir -p build && cd build
```

Run the install command to populate `deployed_app` folder
```bash
cmake --install . --prefix "$(pwd)/deployed_app"
```

Manually add libmpv (only needed for systems that don't have it installed globally)
```bash
cp /usr/lib/x86_64-linux-gnu/libmpv.so.2 "$(pwd)/deployed_app/lib/"
```

### 2. Metadata
Create a .desktop file for the app (e.g., `MediaServerClient.desktop`) with the following content:
```ini
[Desktop Entry]
Type=Application
Name=Media Server Client
Exec=appMediaServerClient
Icon=/path/to/icon.png
Terminal=false
Categories=Multimedia;Video;
```

Copy icon file to the deployed_app folder

Create the entry point symlink for the executable
```bash
ln -sf bin/appMediaServerClient "$PWD/deployed_app/AppRun"
```

### 3. Packaging
Use a tool like `appimagetool` to create an AppImage from the `deployed_app` folder:
```bash
./appimagetool-x86_64.AppImage .../deployed_app/MediaServerClient.AppImage
```