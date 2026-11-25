#!/bin/bash
# Arguments are passed through unchanged:
#   <input_dir> <output_dir> [iter] [rho] [alpha]     (EUCAIM jobman)
#   [iter] [rho] [alpha]                              (uses INPUT_DIR / OUTPUT_DIR, default /input /output)
set -e
echo "=== Starting NLmCED ==="
python3.10 /app/nlmced.py "$@"
echo "=== Completed NLmCED Denoising ==="
