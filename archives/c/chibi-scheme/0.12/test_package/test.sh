#!/bin/sh
# test.sh — chibi-scheme 0.12 test
# Runs the chibi-scheme binary and verifies output
set -euo pipefail
# test.sh — chibi-scheme 0.12 test
# Runs the chibi-scheme binary and verifies output

CHIBI_BIN="${1:-chibi-scheme}"

# Test 1: Basic arithmetic
result=$("$CHIBI_BIN" -e '(display (+ 1 2))')
if [ "$result" = "3" ]; then
    echo "PASS: (+ 1 2) = 3"
else
    echo "FAIL: expected 3, got '$result'"
    exit 1
fi

# Test 2: String output
result=$("$CHIBI_BIN" -e '(display "hello")')
if [ "$result" = "hello" ]; then
    echo "PASS: display hello"
else
    echo "FAIL: expected hello, got '$result'"
    exit 1
fi

# Test 3: List operations
result=$("$CHIBI_BIN" -e '(display (length (list 1 2 3)))')
if [ "$result" = "3" ]; then
    echo "PASS: length of (1 2 3) = 3"
else
    echo "FAIL: expected 3, got '$result'"
    exit 1
fi

echo "All tests passed."
