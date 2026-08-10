#!/bin/bash
# test_lzbench.sh — smoke test for lzbench binary
# Verifies that the lzbench binary is installed, executable, and functional.
# Usage: bash test_lzbench.sh <bin_dir>

set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    # Try to find lzbench in PATH
    BIN_DIR=$(dirname "$(command -v lzbench 2>/dev/null)" 2>/dev/null || echo "")
fi

LZBENCH="${BIN_DIR:+$BIN_DIR/}lzbench"

# Check binary exists and is executable
if [ ! -x "$LZBENCH" ]; then
    echo "FAIL: lzbench binary not found or not executable at $LZBENCH"
    exit 1
fi

# Test: version output
OUTPUT=$("$LZBENCH" -V 2>&1)
if echo "$OUTPUT" | grep -q "lzbench 2.2"; then
    echo "PASS: lzbench -V outputs correct version"
else
    echo "FAIL: lzbench -V does not output version 2.2"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test: help output
OUTPUT=$("$LZBENCH" -h 2>&1)
if echo "$OUTPUT" | grep -q "lzbench"; then
    echo "PASS: lzbench -h displays help"
else
    echo "FAIL: lzbench -h does not display help"
    exit 1
fi

echo "All smoke tests passed."
