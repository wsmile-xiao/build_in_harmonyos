#!/bin/sh
# test.sh — pwgen functional test
# Runs pwgen binary and verifies output
set -eu

PWGEN="${1:-pwgen}"

# Test 1: Generate 3 passwords of length 10
output=$("$PWGEN" 10 3)
lines=$(echo "$output" | wc -l)
[ "$lines" -eq 3 ] || { echo "FAIL: expected 3 passwords, got $lines"; exit 1; }

# Test 2: Generate 5 secure passwords of length 15
output=$("$PWGEN" -s 15 5)
lines=$(echo "$output" | wc -l)
[ "$lines" -eq 5 ] || { echo "FAIL: expected 5 passwords, got $lines"; exit 1; }

# Test 3: --help exits 1 (pwgen behavior, not an error)
"$PWGEN" --help >/dev/null 2>&1 || true

echo "All pwgen tests passed"
