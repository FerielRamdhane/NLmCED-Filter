#!/bin/bash
set -e

INPUT_DIR="${INPUT_DIR:-/input}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"

echo "Running NLmCED Denoising tool"
echo "Input directory:  $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

echo "=== Starting NLmCED ==="
python /app/nlmced.py "$@"
echo "=== Completed NLmCED Denoising ==="
