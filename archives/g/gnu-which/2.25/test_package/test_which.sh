#!/bin/bash
# test_which.sh — verify gnu-which binary works correctly
# Called by test_package/conanfile.py test() method

set -euo pipefail

WHICH_BIN="$1"

if [ -z "$WHICH_BIN" ]; then
    echo "ERROR: which binary path not provided"
    exit 1
fi

# Verify the binary exists and is executable
if [ ! -x "$WHICH_BIN" ]; then
    echo "ERROR: $WHICH_BIN not found or not executable"
    exit 1
fi

# Run version check
output=$("$WHICH_BIN" --version 2>&1)
if echo "$output" | grep -q "GNU which v"; then
    echo "PASS: $output" | head -1
else
    echo "FAIL: unexpected output: $output"
    exit 1
fi
