#!/bin/sh
# test_pigz.sh — functional test for pigz binary
# Called by test_package/conanfile.py test() method
# Usage: test_pigz.sh <pigz_binary_path>

PIGZ="$1"
if [ -z "$PIGZ" ]; then
    echo "ERROR: pigz binary path required"
    exit 1
fi

# Test 1: version check
"$PIGZ" --version || exit 1

# Test 2: compress and decompress round-trip
TEST_FILE="$(mktemp "${TMPDIR:-/tmp}/pigz_test.XXXXXX")"
TEST_CONTENT="Hello, pigz on HarmonyOS! Round-trip compression test."
echo "$TEST_CONTENT" > "$TEST_FILE"

# Compress (keep original with -k, force with -f)
"$PIGZ" -kf "$TEST_FILE" || exit 1

# Decompress
"$PIGZ" -df "$TEST_FILE.gz" || exit 1

# Verify content
RESULT=$(cat "$TEST_FILE")
if [ "$RESULT" = "$TEST_CONTENT" ]; then
    echo "PASS: round-trip compression/decompression verified"
else
    echo "FAIL: content mismatch"
    exit 1
fi

# Cleanup
rm -f "$TEST_FILE" "$TEST_FILE.gz"
echo "All tests passed."
