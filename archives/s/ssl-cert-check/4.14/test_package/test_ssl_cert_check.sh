#!/usr/bin/env bash
# Test source for ssl-cert-check test_package
# Verifies the installed ssl-cert-check binary works correctly.
# This script is referenced by test_package/conanfile.py test() method.

set -e

# Get the binary path from the first argument
BINARY="${1:-ssl-cert-check}"

# Test 1: Version output
OUTPUT=$("$BINARY" -V 2>&1)
if [ "$OUTPUT" = "4.14" ]; then
    echo "PASS: ssl-cert-check -V returns version 4.14"
else
    echo "FAIL: ssl-cert-check -V returned '$OUTPUT', expected '4.14'"
    exit 1
fi

# Test 2: Help output (exits with code 1, which is expected)
OUTPUT=$("$BINARY" -h 2>&1) || true
if echo "$OUTPUT" | grep -q "Usage:"; then
    echo "PASS: ssl-cert-check -h shows usage information"
else
    echo "FAIL: ssl-cert-check -h did not show usage"
    exit 1
fi

echo "All tests passed."
