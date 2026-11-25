#!/bin/bash
# Build the NLmCED images from the repository root.
#
#   ./build.sh xnat                         XNAT image (needs the shared MCR base on this machine)
#   ./build.sh eucaim                       self-contained EUCAIM image (no MATLAB needed)
#
# The version is read from src/nlmced.py, so every image gets the same tag as the code.
set -euo pipefail
cd "$(dirname "$0")"

TARGET="${1:?Usage: ./build.sh xnat | eucaim}"
VERSION=$(grep -oP '^TOOL_VERSION = "\K[^"]+' src/nlmced.py)

case "$TARGET" in
  xnat)
    MCR_BASE="${MCR_BASE:-mcr-riciannoiselevel:r2024b}"
    docker image inspect "$MCR_BASE" > /dev/null 2>&1 \
      || { echo "✗ Shared MATLAB Runtime base '$MCR_BASE' not found on this machine"; exit 1; }
    echo "=== Building nlmced-xnat:${VERSION} on ${MCR_BASE} ==="
    docker build -f xnat/Dockerfile --build-arg MCR_BASE="$MCR_BASE" -t "nlmced-xnat:${VERSION}" .
    ;;
  eucaim)
    echo "=== Building nlmced:${VERSION} (self-contained) ==="
    docker build -f eucaim/Dockerfile -t "nlmced:${VERSION}" .
    ;;
  *)
    echo "Unknown target '$TARGET' (use: xnat | eucaim)"; exit 1 ;;
esac
echo "=== Done ==="
