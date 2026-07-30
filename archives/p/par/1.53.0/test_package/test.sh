#!/bin/sh
# test.sh — par 1.53.0 smoke test
# Verifies that par binary is installed and functional.
# Called by test_package/conanfile.py

set -eu

PAR_BIN="${1:-par}"

# Test 1: version check (par uses boolean option 'version', not --version)
output=$("$PAR_BIN" version < /dev/null 2>&1)
if [ "$output" != "par 1.53.0" ]; then
    echo "FAIL: version check failed, got: $output"
    exit 1
fi
echo "PASS: version check"

# Test 2: basic paragraph reflow
input_file=$(mktemp)
echo "Hello world test paragraph for reflow" > "$input_file"
output=$(cat "$input_file" | "$PAR_BIN" 2>&1)
rm -f "$input_file"
if [ -z "$output" ]; then
    echo "FAIL: reflow produced empty output"
    exit 1
fi
echo "PASS: paragraph reflow"

echo "All tests passed."
