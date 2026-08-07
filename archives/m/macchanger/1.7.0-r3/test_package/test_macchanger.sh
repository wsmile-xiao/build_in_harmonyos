#!/bin/sh
# L1 smoke test: verify macchanger binary runs and reports version.
# This script is called by test_package/conanfile.py test() method.
set -e

BIN_DIR="$1"
MACCHANGER="$BIN_DIR/macchanger"

# Verify binary exists and is executable
if [ ! -x "$MACCHANGER" ]; then
    echo "FAIL: macchanger binary not found or not executable: $MACCHANGER"
    exit 1
fi

# Run --version and check output contains expected string
OUTPUT=$("$MACCHANGER" --version 2>&1)
echo "$OUTPUT" | grep -q "GNU MAC changer"
if [ $? -eq 0 ]; then
    echo "PASS: macchanger --version returned expected output"
    exit 0
else
    echo "FAIL: macchanger --version did not return expected output"
    echo "Got: $OUTPUT"
    exit 1
fi
