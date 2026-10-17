#!/bin/sh
# test.sh — bmd-tools smoke test (R34)
# Runs bmd-streamer --help and verifies version + usage output.
# bmd-streamer exits with code 1 for --help (unrecognized option),
# but still prints version "bmd-streamer 1.0.2" and usage info.
set -euo pipefail

BMD_STREAMER="$1"

if [ -z "$BMD_STREAMER" ]; then
    echo "  [fail] binary path not provided"
    exit 1
fi

if [ ! -f "$BMD_STREAMER" ]; then
    echo "  [fail] binary not found at $BMD_STREAMER"
    exit 1
fi

output=$("$BMD_STREAMER" --help 2>&1) || true

# R34: Verify version string (not just binary name)
if echo "$output" | grep -q "bmd-streamer 1.0.2"; then
    echo "  [ok] bmd-streamer binary is functional (version 1.0.2 confirmed)"
    exit 0
else
    echo "  [fail] bmd-streamer did not produce expected version output"
    echo "$output" | head -5
    exit 1
fi
