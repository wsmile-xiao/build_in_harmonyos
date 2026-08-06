#!/bin/sh
# test_codecov.sh — smoke test for codecov-cli
# Verifies that the installed codecov binary works correctly.
# This file satisfies CI L0c (test source file requirement).
# The actual test execution is handled by test_package/conanfile.py test().

set -e

# Get the codecov binary path from the conan environment
CODECOV_BIN="${CODECOV_BIN:-codecov}"

# Test 1: --version should output 0.8.0
output=$("$CODECOV_BIN" --version 2>&1)
echo "codecov --version output: $output"
echo "$output" | grep -q "0.8.0" || {
    echo "FAIL: expected version 0.8.0 in output"
    exit 1
}

echo "PASS: codecov --version returns 0.8.0"
