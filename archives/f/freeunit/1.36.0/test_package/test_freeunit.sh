#!/bin/sh
# Consumer smoke test for freeunit: verify the packaged unitd daemon
# executes on the target and reports its version.
# Usage: test_freeunit.sh <path-to-unitd>
set -u

UNITD="${1:?usage: test_freeunit.sh <path-to-unitd>}"

passed=0
failed=0

# Case 1: unitd --version prints "unit version: 1.36.0" (to stderr) and exits 0
ver=$("$UNITD" --version 2>&1)
rc=$?
if [ $rc -eq 0 ] && printf '%s' "$ver" | grep -q "unit version: 1.36.0"; then
    echo "PASS: unitd --version -> $ver"
    passed=$((passed + 1))
else
    echo "FAIL: unitd --version rc=$rc output=$ver"
    failed=$((failed + 1))
fi

# Case 2: unitd -h prints help text (mentions unitd options) and exits 0
help_out=$("$UNITD" -h 2>&1)
rc=$?
if [ $rc -eq 0 ] && printf '%s' "$help_out" | grep -q "unit"; then
    echo "PASS: unitd -h"
    passed=$((passed + 1))
else
    echo "FAIL: unitd -h rc=$rc"
    failed=$((failed + 1))
fi

echo "RESULT: passed=$passed failed=$failed"
[ $failed -eq 0 ] || exit 1
exit 0
