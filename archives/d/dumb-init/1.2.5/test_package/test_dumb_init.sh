#!/usr/bin/env bash
# Test script for dumb-init — verifies the binary works correctly.
# Run by test_package/conanfile.py test() method.
# This file satisfies CI L0c (test source file requirement).

set -euo pipefail

DUMB_INIT="${1:-dumb-init}"

# Test 1: --version output
output=$("$DUMB_INIT" --version 2>&1)
if echo "$output" | grep -q "dumb-init v"; then
    echo "PASS: --version returns expected format"
else
    echo "FAIL: --version output unexpected: $output"
    exit 1
fi

# Test 2: --help shows usage
output=$("$DUMB_INIT" --help 2>&1)
if echo "$output" | grep -q "Usage:"; then
    echo "PASS: --help shows usage"
else
    echo "FAIL: --help missing usage info"
    exit 1
fi

echo "All tests passed"
