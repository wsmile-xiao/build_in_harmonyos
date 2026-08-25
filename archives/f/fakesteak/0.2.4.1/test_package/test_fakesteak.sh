#!/bin/bash
# test_fakesteak.sh — L1 test for fakesteak CLI tool
# Runs the fakesteak binary and verifies version/help output.
# Called by test_package/conanfile.py test() method.

set -euo pipefail

FAKESTEAK="$1"

# Test 1: Version output
output=$("$FAKESTEAK" -V 2>&1)
if ! echo "$output" | grep -q "fakesteak 0.2.4"; then
    echo "FAIL: version output does not contain 'fakesteak 0.2.4'"
    echo "Got: $output"
    exit 1
fi

# Test 2: Help output
output=$("$FAKESTEAK" -h 2>&1)
if ! echo "$output" | grep -q "USAGE"; then
    echo "FAIL: help output does not contain 'USAGE'"
    echo "Got: $output"
    exit 1
fi

echo "PASS: fakesteak binary works correctly"
exit 0
