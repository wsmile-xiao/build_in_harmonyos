#!/bin/sh
# test_package/test.sh — run the crunch binary and verify expected output.
# Invoked by conanfile.py test() through CONFIG_SHELL bash (R5: OHOS has no
# /bin/sh, so the shebang above is informational only — bash sources this file).
#
# Usage: test.sh <path-to-crunch-binary>
set -eu

bin="$1"

# Generate 2-char words from charset "ab" → expected: aa, ab, ba, bb
# Use -o to capture output, then count lines
# E002: OHOS /tmp is read-only, use $TMPDIR instead
output=$(mktemp -p "${TMPDIR:-/tmp}" crunch_test_XXXXXX)
trap 'rm -f "$output"' EXIT

"$bin" 2 2 ab -o "$output" 2>/dev/null

# Count lines in output
count=$(wc -l < "$output")

# 2^2 = 4 words expected
if [ "$count" -ne 4 ]; then
    echo "FAIL: expected 4 words, got $count"
    cat "$output"
    exit 1
fi

# Verify expected words
expected_aa=$(grep -c '^aa$' "$output" || true)
expected_bb=$(grep -c '^bb$' "$output" || true)
if [ "$expected_aa" -ne 1 ] || [ "$expected_bb" -ne 1 ]; then
    echo "FAIL: missing expected words"
    cat "$output"
    exit 1
fi

echo "PASS: crunch generated 4 words as expected"