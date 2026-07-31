#!/bin/bash
#
# test_ansiweather.sh — CLI smoke test for ansiweather
# Verifies that:
#   1. ansiweather is installed and executable
#   2. `ansiweather -v` outputs version string "AnsiWeather 1.19.0"
#
# This is a real test (not a dummy always-0 test).

set -euo pipefail

TEST_CMD="${1:-ansiweather}"

echo "=== test_ansiweather: checking $TEST_CMD exists and is executable ==="
if ! command -v "$TEST_CMD" >/dev/null 2>&1; then
    echo "FAIL: $TEST_CMD not found in PATH"
    exit 1
fi

echo "=== test_ansiweather: running $TEST_CMD -v ==="
OUTPUT=$("$TEST_CMD" -v 2>&1) || {
    rc=$?
    echo "FAIL: $TEST_CMD -v returned exit code $rc"
    echo "Output: $OUTPUT"
    exit $rc
}

echo "Output: $OUTPUT"

echo "=== test_ansiweather: checking version string ==="
if echo "$OUTPUT" | grep -q "AnsiWeather 1.19.0"; then
    echo "PASS: version string 'AnsiWeather 1.19.0' found in output"
else
    echo "FAIL: version string 'AnsiWeather 1.19.0' NOT found in output"
    echo "Got: $OUTPUT"
    exit 1
fi

echo "=== test_ansiweather: all checks passed ==="
exit 0
