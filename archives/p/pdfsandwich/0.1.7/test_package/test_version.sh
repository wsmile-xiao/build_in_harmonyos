#!/bin/sh
# test_version.sh — verify pdfsandwich binary works
# CI L0c requires a test source file in test_package/
# This script runs pdfsandwich -version and checks the output

set -e

# Run pdfsandwich -version
output=$(pdfsandwich -version 2>&1)

# Verify output contains version string
if echo "$output" | grep -q "0.1.7"; then
    echo "PASS: pdfsandwich -version returned expected version"
    exit 0
else
    echo "FAIL: pdfsandwich -version did not return expected version"
    echo "Output: $output"
    exit 1
fi
