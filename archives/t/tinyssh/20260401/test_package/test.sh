#!/bin/sh
# test.sh — tinyssh test_package test
# Verifies that tinysshd binary is installed and functional.
# tinysshd with no args prints usage and exits non-zero.

set -e

# Find tinysshd in the Conan environment
TINYSSHD=$(which tinysshd 2>/dev/null || echo "")
if [ -z "$TINYSSHD" ]; then
    # Try common install paths
    for dir in /sbin /usr/sbin /usr/local/sbin; do
        if [ -x "$dir/tinysshd" ]; then
            TINYSSHD="$dir/tinysshd"
            break
        fi
    done
fi

if [ -z "$TINYSSHD" ]; then
    echo "FAIL: tinysshd binary not found"
    exit 1
fi

echo "Found tinysshd at: $TINYSSHD"

# Run tinysshd with no arguments — it should print usage and exit non-zero
output=$("$TINYSSHD" 2>&1) || true
if echo "$output" | grep -q "usage"; then
    echo "PASS: tinysshd prints usage message"
else
    echo "FAIL: tinysshd did not print usage message"
    echo "Output: $output"
    exit 1
fi

# Verify tinysshd-makekey exists
TINYSSHD_MAKEKEY=$(dirname "$TINYSSHD")/tinysshd-makekey
if [ -x "$TINYSSHD_MAKEKEY" ]; then
    echo "PASS: tinysshd-makekey found"
else
    echo "FAIL: tinysshd-makekey not found"
    exit 1
fi

echo "All tests passed."
