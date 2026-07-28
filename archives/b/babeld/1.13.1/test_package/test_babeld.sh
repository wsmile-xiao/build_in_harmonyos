#!/bin/bash
# test_babeld.sh - Functional test for babeld binary
# Verifies that babeld can start and report its version correctly.
# Run by test_package/conanfile.py test() method.
# Usage: test_babeld.sh <path_to_babeld_binary>

set -euo pipefail

BABELD_BIN="${1:-babeld}"

# Test 1: Version output
OUTPUT=$("$BABELD_BIN" -V 2>&1)
if echo "$OUTPUT" | grep -q "babeld-1.13.1"; then
    echo "PASS: babeld -V outputs correct version ($OUTPUT)"
else
    echo "FAIL: babeld -V output unexpected: $OUTPUT"
    exit 1
fi

# Test 2: Help/usage output (babeld prints usage when given -h)
OUTPUT=$("$BABELD_BIN" -h 2>&1 || true)
if echo "$OUTPUT" | grep -q "Syntax:"; then
    echo "PASS: babeld prints usage syntax"
else
    echo "FAIL: babeld usage output unexpected"
    exit 1
fi

echo "All tests passed."
