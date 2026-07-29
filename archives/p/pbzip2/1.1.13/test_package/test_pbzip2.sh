#!/bin/sh
# test_package/test_pbzip2.sh — functional test for pbzip2 1.1.13
#
# This script is invoked by test_package/conanfile.py test() method.
# It creates a test file, compresses it with pbzip2, decompresses it,
# and verifies the result matches the original.
#
# R34: Test must actually exercise the pbzip2 binary (not just print a string).
# Test scripts must use set -euo pipefail and handle errors explicitly.

set -euo pipefail

PBZIP2="${1:-pbzip2}"
TMPDIR="${TMPDIR:-/tmp}"
WORKDIR="$(mktemp -d "${TMPDIR}/pbzip2_test_XXXXXX")"

# Cleanup on exit (success or failure)
cleanup() {
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

echo "=== pbzip2 functional test ==="
echo "Binary: $PBZIP2"
echo "Workdir: $WORKDIR"
echo ""

# Step 1: Verify the binary runs and reports version
# Capture full output to a variable first, then take the first line.
# This avoids SIGPIPE when pbzip2 writes >1 line to a head -1 pipe:
#   with set -o pipefail, head closing the pipe early would make pbzip2
#   exit 141 (128+SIGPIPE) and abort the script at Step 1.
# Use if ! to explicitly check the exit code: under set -e, plain
# assignments with $() are exemption, so a failing pbzip2 --version
# would be silently masked.
echo "[1/5] Checking pbzip2 version..."
if ! VERSION_OUTPUT="$("$PBZIP2" --version 2>&1)"; then
    echo "FAIL: pbzip2 --version exited with error"
    exit 1
fi
echo "$VERSION_OUTPUT" | head -1
echo ""

# Step 2: Create a test file with known content
echo "[2/5] Creating test file..."
TESTFILE="$WORKDIR/test.txt"
EXPECTED="Hello pbzip2! This is a test file for HarmonyOS OHOS aarch64. $(date)"
echo "$EXPECTED" > "$TESTFILE"
ORIG_SIZE=$(wc -c < "$TESTFILE")
echo "Original file size: $ORIG_SIZE bytes"
echo ""

# Step 3: Compress the file
echo "[3/5] Compressing with pbzip2..."
"$PBZIP2" -z -f "$TESTFILE" 2>&1
COMPRESSED="$TESTFILE.bz2"
if [ ! -f "$COMPRESSED" ]; then
    echo "FAIL: Compressed file $COMPRESSED was not created"
    exit 1
fi
COMP_SIZE=$(wc -c < "$COMPRESSED")
echo "Compressed file size: $COMP_SIZE bytes"
echo ""

# Step 4: Decompress the file
echo "[4/5] Decompressing with pbzip2 -d..."
"$PBZIP2" -d -f "$COMPRESSED" 2>&1
if [ ! -f "$TESTFILE" ]; then
    echo "FAIL: Decompressed file $TESTFILE was not created"
    exit 1
fi
DECOMP_SIZE=$(wc -c < "$TESTFILE")
echo "Decompressed file size: $DECOMP_SIZE bytes"
echo ""

# Step 5: Verify content integrity
echo "[5/5] Verifying content integrity..."
ACTUAL="$(cat "$TESTFILE")"
if [ "$ACTUAL" = "$EXPECTED" ]; then
    echo "PASS: Decompressed content matches original"
    echo ""
    echo "=== All tests passed ==="
    exit 0
else
    echo "FAIL: Content mismatch"
    echo "  Expected: $EXPECTED"
    echo "  Actual:   $ACTUAL"
    exit 1
fi
