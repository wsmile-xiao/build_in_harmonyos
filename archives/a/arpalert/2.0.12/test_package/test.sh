#!/bin/sh
# test.sh — arpalert test_package test script
# R34: Substantively depends on the tested package by running the arpalert binary.
# Verifies the binary is executable and outputs correct help/version information.

set -e

# Find the arpalert binary from the Conan package
ARPALERT_BIN="${1:-arpalert}"

# Test 1: Help flag — verifies binary is executable and linked correctly
echo "=== Test 1: arpalert -h ==="
"$ARPALERT_BIN" -h 2>&1 | grep -q "arpalert" && echo "PASS: help output contains 'arpalert'" || {
    echo "FAIL: help output does not contain 'arpalert'"
    exit 1
}

# Test 2: Version flag — verifies binary version matches package version
echo "=== Test 2: arpalert -V ==="
"$ARPALERT_BIN" -V 2>&1 | grep -q "2.0" && echo "PASS: version output contains '2.0'" || {
    echo "FAIL: version output does not contain '2.0'"
    exit 1
}

echo "=== All tests passed ==="
