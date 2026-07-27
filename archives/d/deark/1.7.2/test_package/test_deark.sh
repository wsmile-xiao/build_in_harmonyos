#!/bin/sh
# test_deark.sh — L1 test for deark binary
# Usage: test_deark.sh /path/to/deark
set -eu

DEARK="$1"
if [ -z "$DEARK" ]; then
    echo "ERROR: deark binary path not provided"
    exit 1
fi

# Test 1: version output
output=$("$DEARK" --version 2>&1)
echo "$output" | grep -q "Deark version: 1.7.2" || {
    echo "FAIL: version output unexpected: $output"
    exit 1
}
echo "PASS: deark --version returns correct version"

# Test 2: module listing (smoke test)
output=$("$DEARK" -modules 2>&1 | head -1)
[ -n "$output" ] || {
    echo "FAIL: module listing empty"
    exit 1
}
echo "PASS: deark -modules lists modules"

# Test 3: license output
output=$("$DEARK" --license 2>&1)
echo "$output" | grep -q "Permission is hereby granted" || {
    echo "FAIL: license output unexpected: $output"
    exit 1
}
echo "PASS: deark --license shows license text"

echo "All tests passed."
