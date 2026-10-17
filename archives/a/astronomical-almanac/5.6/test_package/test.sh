#!/usr/bin/env bash
# test_package/test.sh — smoke test for astronomical-almanac
set -euo pipefail

echo "[test] Checking aa binary exists"
if ! command -v aa >/dev/null 2>&1; then
    echo "FAIL: aa binary not found in PATH"
    exit 1
fi
echo "PASS: aa binary found"

echo "[test] aa smoke test — run with minimal input to verify it starts"
# The program reads interactively; provide minimal date input then exit via planet=-1.
# Input: year 2000, month 1, day 1, 0h 0m 0s, interval=1, count=1, planet=-1 (exit)
output=$(printf '2000\n1\n1\n0\n0\n0\n1\n1\n-1\n' | aa 2>&1)
if [ $? -eq 0 ] && echo "$output" | grep -q "Julian day"; then
    echo "PASS: aa produced output with Julian day"
else
    echo "FAIL: aa did not produce expected output"
    echo "Output was: $output"
    exit 1
fi

echo "[test] All tests passed"
