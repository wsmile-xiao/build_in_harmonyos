#!/bin/sh
# test_jpeginfo.sh — Test jpeginfo binary functionality
# Used by Conan test_package/conanfile.py test() method
#
# Tests:
# 1. --version output contains version string
# 2. JPEG file processing produces expected output
# 3. Integrity check mode works

set -eu

BIN="$1"
TEST_JPG="$2"

# Test 1: version output
VERSION_OUTPUT=$("$BIN" --version 2>&1)
echo "$VERSION_OUTPUT" | grep -q "jpeginfo" || { echo "FAIL: version output missing"; exit 1; }
echo "PASS: version output"

# Test 2: process a JPEG file
INFO_OUTPUT=$("$BIN" "$TEST_JPG" 2>&1)
echo "$INFO_OUTPUT" | grep -q "1 x" || { echo "FAIL: JPEG processing output incorrect"; exit 1; }
echo "PASS: JPEG processing"

# Test 3: check mode (integrity verification)
# jpeginfo -c returns exit code 1 for warnings (expected for minimal test JPEG).
# We capture the exit code and verify it is 0 or 1 (not a crash/error like 127/139/2).
CHECK_EXIT=0
"$BIN" -c "$TEST_JPG" 2>&1 || CHECK_EXIT=$?
if [ "$CHECK_EXIT" -eq 0 ] || [ "$CHECK_EXIT" -eq 1 ]; then
    echo "PASS: integrity check mode (exit=$CHECK_EXIT)"
else
    echo "FAIL: integrity check mode returned unexpected exit code $CHECK_EXIT"
    exit 1
fi

echo "All tests passed."
