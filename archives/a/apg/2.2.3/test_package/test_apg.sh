#!/bin/bash
set -euo pipefail
# test_apg.sh — smoke test for apg binary
# This script verifies that the apg binary can generate passwords.
# It is also a placeholder test source file required by CI L0c check.

APG_BIN="${1:-apg}"

# Test 1: version check
output=$("$APG_BIN" -v 2>&1)
if echo "$output" | grep -q "APG"; then
    echo "[ok] version check passed"
else
    echo "[fail] version check failed: $output"
    exit 1
fi

# Test 2: password generation
output=$("$APG_BIN" -n 5 -m 8 -x 10 2>&1)
lines=$(echo "$output" | wc -l)
if [ "$lines" -ge 5 ]; then
    echo "[ok] password generation passed ($lines passwords)"
else
    echo "[fail] password generation failed: expected 5 passwords, got $lines"
    exit 1
fi

echo "[ok] all tests passed"
