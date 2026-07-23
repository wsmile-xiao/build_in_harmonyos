#!/bin/bash
# test_mmv.sh — verify mmv binary can move/copy/symlink files.
# Adapted from Homebrew mmv formula test.
# Usage: test_mmv.sh <path-to-mmv-binary>

set -euo pipefail

MMV_BIN="$1"

if [ -z "$MMV_BIN" ]; then
    echo "ERROR: mmv binary path not provided"
    exit 1
fi

if [ ! -x "$MMV_BIN" ]; then
    echo "ERROR: $MMV_BIN not found or not executable"
    exit 1
fi

# Create a temporary working directory
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

ASSERTION_COUNT=0
pass() {
    ASSERTION_COUNT=$((ASSERTION_COUNT + 1))
    echo "PASS: $1"
}
fail() {
    echo "FAIL: $1"
    exit 1
}

# Test 1: mmv -p (preview) should refuse to overwrite existing file
echo "a" > a
echo "b" > b
output=$("$MMV_BIN" -p a b 2>&1) && rc=0 || rc=$?
if [ "$rc" -ne 1 ]; then
    fail "mmv -p a b should exit with code 1, got $rc"
fi
if ! echo "$output" | grep -q "old b would have to be deleted"; then
    fail "mmv -p a b should warn about deletion, got: $output"
fi
[ -f a ] || fail "file 'a' should still exist after preview"
pass "mmv -p correctly previews and refuses overwrite"

# Test 2: mmv -d -v (delete+verbose) should move a over b
output=$("$MMV_BIN" -d -v a b 2>&1)
if ! echo "$output" | grep -q "a -> b.*: done"; then
    fail "mmv -d -v a b should report done, got: $output"
fi
[ ! -f a ] || fail "file 'a' should be gone after move"
[ -f b ] || fail "file 'b' should exist after move"
content=$(cat b)
if [ "$content" != "a" ]; then
    fail "file 'b' should contain 'a', got '$content'"
fi
pass "mmv -d -v correctly moves and overwrites"

# Test 3: mmv -s -v (symlink+verbose) should create a symlink
output=$("$MMV_BIN" -s -v b c 2>&1)
if ! echo "$output" | grep -q "b -> c : done"; then
    fail "mmv -s -v b c should report done, got: $output"
fi
[ -f b ] || fail "file 'b' should still exist after symlink"
[ -L c ] || fail "file 'c' should be a symlink"
content=$(cat c)
if [ "$content" != "a" ]; then
    fail "symlink 'c' should resolve to 'a', got '$content'"
fi
pass "mmv -s -v correctly creates symlink"

echo ""
echo "All $ASSERTION_COUNT assertions passed."
