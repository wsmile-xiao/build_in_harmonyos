#!/bin/sh
# L1 smoke test: verify ffprobe binary is functional
# R34: Test genuinely depends on the ffprobe package
set -e

FFPROBE="${1:-ffprobe}"

# Verify ffprobe can report its version (binary is functional)
"$FFPROBE" -version

echo "PASS: ffprobe smoke test"
