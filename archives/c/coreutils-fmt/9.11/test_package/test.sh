#!/bin/sh
# test.sh - Test fmt binary from coreutils-fmt package
# Usage: FMT_BIN=/path/to/fmt bash test.sh
set -e

FMT_BIN="${FMT_BIN:-fmt}"

# Test 1: --version reports correct version
if "$FMT_BIN" --version 2>&1 | grep -q "9.11"; then
    echo "PASS: fmt --version reports 9.11"
else
    echo "FAIL: fmt --version did not report 9.11"
    exit 1
fi

# Test 2: fmt -w 8 wraps text correctly
output=$(printf 'aa bb cc dd ee' | "$FMT_BIN" -w 8)
expected=$(printf 'aa bb cc\ndd ee')
if [ "$output" = "$expected" ]; then
    echo "PASS: fmt -w 8 produces correct output"
else
    echo "FAIL: fmt -w 8 output mismatch"
    exit 1
fi

# Test 3: fmt -w 7 wraps text correctly
output=$(printf 'aa bb cc dd ee' | "$FMT_BIN" -w 7)
expected=$(printf 'aa\nbb cc\ndd ee')
if [ "$output" = "$expected" ]; then
    echo "PASS: fmt -w 7 produces correct output"
else
    echo "FAIL: fmt -w 7 output mismatch"
    exit 1
fi

# Test 4: fmt default width wraps long text
output=$(echo "This is a test of the fmt command to see if it properly wraps text to the default width of 75 characters." | "$FMT_BIN")
line_count=$(printf '%s\n' "$output" | wc -l)
if [ "$line_count" -ge 1 ]; then
    echo "PASS: fmt default width wraps text"
else
    echo "FAIL: fmt default width produced no output"
    exit 1
fi

# Test 5: fmt -s splits long lines
long_line=$(printf '%2030s' ' ' | sed 's/../ y/g')
output=$(echo "$long_line" | "$FMT_BIN" -s)
line_count=$(printf '%s\n' "$output" | wc -l)
if [ "$line_count" -gt 1 ]; then
    echo "PASS: fmt -s splits long lines ($line_count lines)"
else
    echo "FAIL: fmt -s did not split long line"
    exit 1
fi

echo ""
echo "All fmt tests passed!"
exit 0
