#!/bin/bash
set -e

INPUT_DIR="${1:-/input}"
OUTPUT_DIR="${2:-/output}"
# Now shift these first two positional parameters if exists
shift $(( $# < 2 ? $# : 2 ))

echo "Running NLmCED Denoising tool"
echo "Input directory:  $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

echo "=== Starting NLmCED ==="
python /app/nlmced.py "$@"
echo "=== Completed NLmCED Denoising ==="
