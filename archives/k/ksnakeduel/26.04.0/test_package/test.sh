#!/bin/sh
# test.sh — ksnakeduel runtime smoke test
# Usage: test.sh <path-to-ksnakeduel-binary>
# Asserts:
#   1. binary exists and is executable
#   2. ksnakeduel --version prints version string and exits 0

set -e

BINARY="$1"

if [ -z "$BINARY" ]; then
    echo "FAIL: no binary path provided"
    exit 1
fi

if [ ! -f "$BINARY" ]; then
    echo "FAIL: binary not found: $BINARY"
    exit 1
fi

if [ ! -x "$BINARY" ]; then
    echo "FAIL: binary not executable: $BINARY"
    exit 1
fi

echo "PASS: binary exists and is executable: $BINARY"

# Test --version (QCommandLineParser handles it before GUI creation)
VERSION_OUTPUT=$("$BINARY" --version 2>&1) || {
    echo "FAIL: ksnakeduel --version exited non-zero"
    echo "Output: $VERSION_OUTPUT"
    exit 1
}

echo "$VERSION_OUTPUT" | grep -qi "ksnakeduel\|26.04" || {
    echo "FAIL: --version output does not contain expected version string"
    echo "Output: $VERSION_OUTPUT"
    exit 1
}

echo "PASS: ksnakeduel --version output: $VERSION_OUTPUT"
echo "ALL TESTS PASSED"
