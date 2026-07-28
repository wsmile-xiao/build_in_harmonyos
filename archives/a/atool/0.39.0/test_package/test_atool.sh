#!/bin/bash
# test_atool.sh — verify atool commands via functional smoke test.
# Usage: test_atool.sh <path-to-atool-package-folder>
#
# Test logic follows Homebrew formula:
#   1. atool --version outputs version info
#   2. apack creates a tar.gz archive from test files
#   3. als lists archive contents and verifies test file names appear

set -euo pipefail

PKG_DIR="$1"

if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder not provided"
    exit 1
fi

BIN_DIR="$PKG_DIR/bin"

if [ ! -x "$BIN_DIR/atool" ]; then
    echo "ERROR: $BIN_DIR/atool not found or not executable"
    exit 1
fi

ASSERTION_COUNT=0
pass() {
    ASSERTION_COUNT=$((ASSERTION_COUNT + 1))
    echo "PASS: $1"
}
fail() {
    echo "FAIL: $1"
    exit 1
}

# Test 1: atool --version outputs version string
output=$("$BIN_DIR/atool" --version 2>&1) || fail "atool --version failed to run"
echo "$output" | grep -q "atool" || fail "atool --version should contain 'atool', got: $output"
pass "atool --version outputs version info"

# Test 2: apack creates a tar.gz archive and als lists its contents
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "example" > "$WORKDIR/example.txt"
echo "example2" > "$WORKDIR/example2.txt"

cd "$WORKDIR"
"$BIN_DIR/apack" test.tar.gz example.txt example2.txt >/dev/null 2>&1 \
    || fail "apack failed to create tar.gz archive"

if [ ! -f "$WORKDIR/test.tar.gz" ]; then
    fail "apack did not produce test.tar.gz"
fi
pass "apack creates tar.gz archive"

# Test 3: als lists archive contents
output=$("$BIN_DIR/als" "$WORKDIR/test.tar.gz" 2>&1) \
    || fail "als failed to list archive contents"
echo "$output" | grep -q "example.txt" || fail "als output should contain 'example.txt', got: $output"
echo "$output" | grep -q "example2.txt" || fail "als output should contain 'example2.txt', got: $output"
pass "als lists archive contents correctly"

echo ""
echo "All $ASSERTION_COUNT assertions passed."
