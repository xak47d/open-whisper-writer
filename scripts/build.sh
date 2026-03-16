#!/usr/bin/env bash
#
# Build WhisperWriter standalone binary using PyInstaller.
#
# Usage:
#   ./scripts/build.sh
#
# Prerequisites:
#   pip install -e ".[dev]"
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "==> Building WhisperWriter with PyInstaller..."
echo "    Project root: $PROJECT_ROOT"

cd "$PROJECT_ROOT"

# Clean previous builds
rm -rf build/whisper-writer dist/whisper-writer

# Run PyInstaller
pyinstaller \
    --noconfirm \
    --clean \
    whisper-writer.spec

echo "==> Build complete!"
echo "    Output: $PROJECT_ROOT/dist/whisper-writer/"
echo ""
echo "    Run with: ./dist/whisper-writer/whisper-writer"
