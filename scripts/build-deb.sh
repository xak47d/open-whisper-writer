#!/usr/bin/env bash
#
# Build a .deb package for WhisperWriter.
#
# Usage:
#   ./scripts/build-deb.sh [version]
#
# Prerequisites:
#   - PyInstaller build must be completed first (run ./scripts/build.sh)
#   - dpkg-deb must be available
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VERSION="${1:-1.1.0}"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG_NAME="whisper-writer"
PKG_DIR="$PROJECT_ROOT/build/${PKG_NAME}_${VERSION}_${ARCH}"

echo "==> Building .deb package: ${PKG_NAME}_${VERSION}_${ARCH}.deb"

# Ensure PyInstaller output exists
if [ ! -d "$PROJECT_ROOT/dist/whisper-writer" ]; then
    echo "ERROR: PyInstaller build not found at dist/whisper-writer/"
    echo "       Run ./scripts/build.sh first."
    exit 1
fi

# Clean previous package build
rm -rf "$PKG_DIR"

# Create directory structure
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/opt/whisper-writer"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$PKG_DIR/usr/share/metainfo"

# Copy PyInstaller output
cp -r "$PROJECT_ROOT/dist/whisper-writer/"* "$PKG_DIR/opt/whisper-writer/"

# Create symlink wrapper
cat > "$PKG_DIR/usr/bin/whisper-writer" << 'WRAPPER'
#!/bin/sh
exec /opt/whisper-writer/whisper-writer "$@"
WRAPPER
chmod 755 "$PKG_DIR/usr/bin/whisper-writer"

# Copy desktop file (update Exec and Icon paths)
sed \
    -e 's|^Exec=.*|Exec=/opt/whisper-writer/whisper-writer|' \
    -e 's|^Icon=.*|Icon=whisper-writer|' \
    "$PROJECT_ROOT/whisper-writer.desktop" > "$PKG_DIR/usr/share/applications/whisper-writer.desktop"

# Copy icon
cp "$PROJECT_ROOT/assets/ww-logo.png" "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/whisper-writer.png"

# Copy AppStream metadata
cp "$PROJECT_ROOT/io.github.xak47d.whisper-writer.metainfo.xml" "$PKG_DIR/usr/share/metainfo/"

# Calculate installed size (in KB)
INSTALLED_SIZE=$(du -sk "$PKG_DIR" | cut -f1)

# Generate DEBIAN/control
cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: ${ARCH}
Installed-Size: ${INSTALLED_SIZE}
Depends: libportaudio2, libsndfile1, libxcb-xinerama0, libxkbcommon0, libgl1
Recommends: libcudart12, libcublas12
Description: Speech-to-text voice typing powered by OpenAI Whisper
 WhisperWriter is a speech-to-text desktop application that runs in the
 background and automatically transcribes your speech into the currently
 active window. Supports local faster-whisper models (tiny through
 large-v3-turbo) and the OpenAI API.
Maintainer: xak47d <https://github.com/xak47d>
Homepage: https://github.com/xak47d/open-whisper-writer
EOF

# Post-install script
cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

# Post-remove script
cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q /usr/share/icons/hicolor || true
fi
EOF
chmod 755 "$PKG_DIR/DEBIAN/postrm"

# Build the .deb
dpkg-deb --build --root-owner-group "$PKG_DIR"

# Move to dist/
mkdir -p "$PROJECT_ROOT/dist"
mv "$PKG_DIR.deb" "$PROJECT_ROOT/dist/"

echo "==> Package built: dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo ""
echo "    Install with: sudo dpkg -i dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
echo "    Or:           sudo apt install ./dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"
