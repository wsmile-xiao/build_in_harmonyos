#!/bin/sh
# test_gping.sh — L1 test source for gping
# Runs gping --version to verify the binary is functional
set -e

GPING_BIN="${1:-gping}"

if ! "$GPING_BIN" --version >/dev/null 2>&1; then
    echo "FAIL: gping --version did not return success"
    exit 1
fi

# Verify version string contains "gping"
OUTPUT=$("$GPING_BIN" --version 2>&1)
if echo "$OUTPUT" | grep -q "gping"; then
    echo "PASS: gping --version returns correct version string"
    exit 0
else
    echo "FAIL: gping --version output does not contain 'gping'"
    exit 1
fi
