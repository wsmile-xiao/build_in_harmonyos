#!/bin/sh
set -eu

ALASS="$1"
PASSED=0
TOTAL=5

fail_test() {
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"alass-cli consumer smoke\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
    exit 1
}

VERSION_OUTPUT=$("$ALASS" --version 2>&1) || fail_test
printf '%s\n' "$VERSION_OUTPUT"
printf '%s\n' "$VERSION_OUTPUT" | grep -F "2.0.0" >/dev/null || fail_test
PASSED=$((PASSED + 1))

HELP_OUTPUT=$("$ALASS" --help 2>&1) || fail_test
printf '%s\n' "$HELP_OUTPUT" | grep -F "reference-file" >/dev/null || fail_test
PASSED=$((PASSED + 1))

SYNC_OUTPUT=$("$ALASS" reference.srt incorrect.srt output.srt 2>&1) || fail_test
printf '%s\n' "$SYNC_OUTPUT"
printf '%s\n' "$SYNC_OUTPUT" | grep -F "shifted block of 1 subtitles with length 0:00:00.000 by -0:00:01.000" >/dev/null || fail_test
PASSED=$((PASSED + 1))

grep -F "00:00:00,000 --> 00:00:01,000" output.srt >/dev/null || fail_test
PASSED=$((PASSED + 1))

grep -F "This is the first subtitle." output.srt >/dev/null || fail_test
PASSED=$((PASSED + 1))

printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"alass-cli consumer smoke\",\"discovered\":${TOTAL},\"passedCount\":${PASSED}}"
