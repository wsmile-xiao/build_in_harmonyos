#!/bin/bash
# test_patch.sh — verify gpatch binary works correctly
# Called by test_package/conanfile.py test() method

set -euo pipefail

PATCH_BIN="$1"

if [ -z "$PATCH_BIN" ]; then
    echo "ERROR: patch binary path not provided"
    exit 1
fi

# Verify the binary exists and is executable
if [ ! -x "$PATCH_BIN" ]; then
    echo "ERROR: $PATCH_BIN not found or not executable"
    exit 1
fi

# Test 1: Version check
output=$("$PATCH_BIN" --version 2>&1)
if echo "$output" | grep -q "GNU patch"; then
    echo "PASS: $(echo "$output" | head -1)"
else
    echo "FAIL: unexpected version output: $output"
    exit 1
fi

# Test 2: Basic patch application
# E002: /tmp is read-only on HarmonyOS, use $HOME/tmp
TEST_DIR="${HOME}/tmp/gpatch_test_$$"
mkdir -p "$TEST_DIR"
trap "rm -rf $TEST_DIR" EXIT

echo "original content" > "$TEST_DIR/file.txt"
echo "modified content" > "$TEST_DIR/file_new.txt"
# diff returns 1 when files differ — expected, not an error
diff -u "$TEST_DIR/file.txt" "$TEST_DIR/file_new.txt" > "$TEST_DIR/changes.patch" || rc=$?
if [ ! -s "$TEST_DIR/changes.patch" ]; then
    echo "FAIL: diff produced empty patch file"
    exit 1
fi

"$PATCH_BIN" "$TEST_DIR/file.txt" < "$TEST_DIR/changes.patch"

if grep -q "modified content" "$TEST_DIR/file.txt"; then
    echo "PASS: patch applied correctly"
else
    echo "FAIL: patch was not applied"
    exit 1
fi

# Test 3: Patch reversal
"$PATCH_BIN" -R "$TEST_DIR/file.txt" < "$TEST_DIR/changes.patch"

if grep -q "original content" "$TEST_DIR/file.txt"; then
    echo "PASS: patch reversed correctly"
else
    echo "FAIL: patch reversal failed"
    exit 1
fi
