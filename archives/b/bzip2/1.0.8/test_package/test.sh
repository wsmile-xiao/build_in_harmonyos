#!/usr/bin/env bash
# test_package/test.sh — bzip2 1.0.8 smoke test
# Verifies compression and decompression with content integrity check.

set -euo pipefail

# Create a test file with known content in the test package work directory.
TEST_FILE="bzip2_test_$$.txt"
trap 'rm -f "${TEST_FILE}" "${TEST_FILE}.bz2" "${TEST_FILE}.out"' EXIT

echo "bzip2 smoke test: hello from OHOS" > "${TEST_FILE}"

# Compress with -k (keep original)
bzip2 -k "${TEST_FILE}"
if [ ! -f "${TEST_FILE}.bz2" ]; then
    echo "FAIL: compressed file not found"
    exit 1
fi

# Decompress to stdout and compare
bzip2 -dc "${TEST_FILE}.bz2" > "${TEST_FILE}.out"
if ! diff "${TEST_FILE}" "${TEST_FILE}.out" >/dev/null 2>&1; then
    echo "FAIL: decompressed content differs from original"
    exit 1
fi

echo "PASS: bzip2 compression/decompression verified"
