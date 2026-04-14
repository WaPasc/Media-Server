# Build Executable (Linux)

## 1. Configure release build

```bash
mkdir -p build && cd build

/home/yourUserName/Qt/Tools/CMake/bin/cmake \
  -DCMAKE_PREFIX_PATH=/home/yourUserName/Qt/6.10.2/gcc_64 \
  -DCMAKE_BUILD_TYPE=Release ..
```

## 2. Build and install into AppDir

```bash
cmake --build . --config Release
cmake --install . --prefix "$PWD/deployed_app"
```

## 3. Bundle runtime dependency (libmpv)

Run this only if `libmpv` is not guaranteed on the target machine.

```bash
mkdir -p "$PWD/deployed_app/lib"
cp /usr/lib/x86_64-linux-gnu/libmpv.so.2 "$PWD/deployed_app/lib/"
```

## 4. Add AppImage metadata

Create `deployed_app/MediaServerClient.desktop`:

```ini
[Desktop Entry]
Type=Application
Name=Media Server Client
Exec=appMediaServerClient
Icon=MediaServerClient
Terminal=false
Categories=Multimedia;Video;
```
make sure to not use the extenstion of the icon file in the `Icon` field.
Copy your icon to `deployed_app/MediaServerClient.png`.

Create the AppImage entry point:

```bash
ln -sf bin/appMediaServerClient "$PWD/deployed_app/AppRun"
```

## 5. Package

```bash
./appimagetool-x86_64.AppImage "$PWD/deployed_app" "$PWD/MediaServerClient-x86_64.AppImage"
```




# Rerunning the cycle

**Rebuild**: `cmake --build . --config Release` inside the build folder.

**Redeploy**: `cmake --install . --prefix "$PWD/deployed_app"`

**Repackage**: Run appimagetool on the deployed_app folder again.