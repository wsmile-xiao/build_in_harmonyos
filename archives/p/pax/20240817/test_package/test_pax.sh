#!/bin/sh
# test_pax.sh — L1 test for pax 20240817
# Tests: create archive, list archive, extract archive, verify content

set -e

PAX_BIN="${1:-pax}"
TESTDIR="${TMPDIR:-/tmp}/pax-l1-test-$$"
ARCHIVE="$TESTDIR/test.tar"
EXTRACTDIR="$TESTDIR/extract"

cleanup() {
    rm -rf "$TESTDIR"
}
trap cleanup EXIT

mkdir -p "$TESTDIR/subdir"
echo "hello world" > "$TESTDIR/file1.txt"
echo "nested" > "$TESTDIR/subdir/file2.txt"

# Test 1: Create archive
cd "$TESTDIR"
$PAX_BIN -w -x ustar -f "$ARCHIVE" . 2>/dev/null || true
if [ ! -f "$ARCHIVE" ]; then
    echo "FAIL: archive not created"
    exit 1
fi
echo "PASS: archive created"

# Test 2: List archive
$PAX_BIN -f "$ARCHIVE" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "FAIL: cannot list archive"
    exit 1
fi
echo "PASS: archive listed"

# Test 3: Extract archive
mkdir -p "$EXTRACTDIR"
cd "$EXTRACTDIR"
$PAX_BIN -r -f "$ARCHIVE" 2>/dev/null
if [ ! -f "$EXTRACTDIR/file1.txt" ]; then
    echo "FAIL: extracted file1.txt not found"
    exit 1
fi
echo "PASS: archive extracted"

# Test 4: Verify content
CONTENT=$(cat "$EXTRACTDIR/file1.txt")
if [ "$CONTENT" != "hello world" ]; then
    echo "FAIL: content mismatch: '$CONTENT'"
    exit 1
fi
echo "PASS: content verified"

echo "All tests passed"
exit 0
