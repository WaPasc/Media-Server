#!/usr/bin/env bash
# Build a fresh release AppImage of MediaServerClient and drop it where the
# existing ~/.local/share/applications/MediaServerClient.desktop entry points.
#
# What it does, in order:
#   1. Configure / build the release target with the project's Qt toolchain.
#   2. Install into build/deployed_app (the AppDir).
#   3. Bundle libmpv.so.2 next to the binary (skipped if libmpv is missing
#      from the host).
#   4. Ensure the AppDir has a valid .desktop file, icon, and AppRun symlink.
#   5. Run appimagetool to produce the final AppImage at
#      ~/apps/Media_Server_Client-x86_64.AppImage (the path the existing
#      desktop entry already references).
#
# Re-runs are safe, it reuses the build directory and just rebuilds.

set -euo pipefail

# --- Paths ----------------------------------------------------------------
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
APPDIR="$BUILD_DIR/deployed_app"

# Defaults match the Qt Online Installer layout. Override any of these by
# exporting them, e.g.: QT_PREFIX=/opt/qt6 ./build-appimage.sh
QT_VERSION="${QT_VERSION:-6.10.2}"
QT_PREFIX="${QT_PREFIX:-$HOME/Qt/$QT_VERSION/gcc_64}"
QT_CMAKE="${QT_CMAKE:-$HOME/Qt/Tools/CMake/bin/cmake}"

APPIMAGETOOL="${APPIMAGETOOL:-$HOME/apps/appimagetool-x86_64.AppImage}"
OUTPUT_APPIMAGE="${OUTPUT_APPIMAGE:-$HOME/apps/Media_Server_Client-x86_64.AppImage}"

ICON_SRC="$APPDIR/mediaIcon.svg"   # icon already lives in the AppDir

LIBMPV_SRC="/usr/lib/x86_64-linux-gnu/libmpv.so.2"

# --- Sanity checks --------------------------------------------------------
if [[ ! -x "$QT_CMAKE" ]]; then
  echo "ERROR: Qt CMake not found at $QT_CMAKE" >&2
  echo "       Edit QT_VERSION / QT_CMAKE at the top of this script." >&2
  exit 1
fi
if [[ ! -d "$QT_PREFIX" ]]; then
  echo "ERROR: Qt prefix not found at $QT_PREFIX" >&2
  exit 1
fi
if [[ ! -x "$APPIMAGETOOL" ]]; then
  echo "ERROR: appimagetool not found at $APPIMAGETOOL" >&2
  exit 1
fi

# --- 1. Configure (only if no cache yet) ---------------------------------
mkdir -p "$BUILD_DIR"
if [[ ! -f "$BUILD_DIR/CMakeCache.txt" ]]; then
  echo ">>> Configuring release build"
  "$QT_CMAKE" \
    -S "$PROJECT_DIR" \
    -B "$BUILD_DIR" \
    -DCMAKE_PREFIX_PATH="$QT_PREFIX" \
    -DCMAKE_BUILD_TYPE=Release
fi

# --- 2. Build + install --------------------------------------------------
echo ">>> Building"
"$QT_CMAKE" --build "$BUILD_DIR" --config Release --parallel

echo ">>> Installing into $APPDIR"
"$QT_CMAKE" --install "$BUILD_DIR" --prefix "$APPDIR"

# --- 3. Bundle libmpv (best-effort) --------------------------------------
if [[ -f "$LIBMPV_SRC" ]]; then
  mkdir -p "$APPDIR/lib"
  cp -f "$LIBMPV_SRC" "$APPDIR/lib/"
  echo ">>> Bundled $(basename "$LIBMPV_SRC")"
else
  echo ">>> Skipping libmpv bundle (not present at $LIBMPV_SRC)"
fi

# --- 4. AppDir metadata --------------------------------------------------
DESKTOP_FILE="$APPDIR/MediaServerClient.desktop"
if [[ ! -f "$DESKTOP_FILE" ]]; then
  echo ">>> Writing $DESKTOP_FILE"
  cat > "$DESKTOP_FILE" <<'EOF'
[Desktop Entry]
Type=Application
Name=Media Server Client
Exec=appMediaServerClient
Icon=mediaIcon
Terminal=false
Categories=Video;Player;
EOF
fi

if [[ ! -f "$ICON_SRC" ]]; then
  echo "ERROR: Icon missing at $ICON_SRC" >&2
  echo "       The .desktop file references 'mediaIcon' (no extension)," >&2
  echo "       so the icon must live next to it as mediaIcon.svg/.png." >&2
  exit 1
fi

# AppRun symlink, appimagetool requires it at the AppDir root.
ln -sfn bin/appMediaServerClient "$APPDIR/AppRun"

# --- 5. Package ----------------------------------------------------------
echo ">>> Packaging AppImage -> $OUTPUT_APPIMAGE"
mkdir -p "$(dirname "$OUTPUT_APPIMAGE")"
"$APPIMAGETOOL" "$APPDIR" "$OUTPUT_APPIMAGE"

echo
echo "Done."
echo "  AppImage: $OUTPUT_APPIMAGE"
echo "  Launcher: ~/.local/share/applications/MediaServerClient.desktop"
