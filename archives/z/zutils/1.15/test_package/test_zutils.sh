#!/bin/bash
# test_zutils.sh — functional test for zutils package
# Creates a gzip-compressed file, decompresses with zcat, and verifies output.
set -euo pipefail

TMPDIR="${TMPDIR:-/tmp}"
TEST_FILE="$TMPDIR/zutils_test_input.txt"
echo "Hello from zutils test" > "$TEST_FILE"
gzip -f "$TEST_FILE"

# Test: zcat can decompress
result=$(zcat "${TEST_FILE}.gz")
if [ "$result" = "Hello from zutils test" ]; then
    echo "PASS: zcat decompression works"
else
    echo "FAIL: zcat output mismatch"
    echo "  expected: Hello from zutils test"
    echo "  got: $result"
    exit 1
fi

# Test: version check
zcat --version 2>&1 | grep -q "1.15"
echo "PASS: zcat --version reports 1.15"

# Test: ztest works
ztest --version 2>&1 | grep -q "zutils"
echo "PASS: ztest --version works"

# Cleanup
rm -f "${TEST_FILE}.gz"

echo "All zutils tests passed"
