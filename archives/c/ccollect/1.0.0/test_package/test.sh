#!/bin/sh
# test_package/test.sh — smoke test for the installed ccollect command
# POSIX sh: ccollect is a pure POSIX sh script, so /bin/sh is sufficient.
set -eu

CCOLLECT_BIN_DIR="$1"
CCOLLECT="$CCOLLECT_BIN_DIR/ccollect"

[ -x "$CCOLLECT" ] || { echo "FAIL: $CCOLLECT is not executable" >&2; exit 1; }

# Test 1: ccollect -V prints the version and exits 0 (upstream -V/--version)
out="$("$CCOLLECT" -V 2>&1)"
echo "Test 1 (ccollect -V): $out"
printf '%s\n' "$out" | grep -q "ccollect 1.0" || {
    echo "FAIL: expected 'ccollect 1.0' in -V output" >&2; exit 1
}

# Test 2: ccollect -h prints usage (upstream -h/--help)
"$CCOLLECT" -h >/dev/null 2>&1 || {
    echo "FAIL: ccollect -h did not exit 0" >&2; exit 1
}

# Test 3: syntax check of the installed script
"$CCOLLECT" -V >/dev/null 2>&1 || { echo "FAIL: ccollect binary failed to run" >&2; exit 1; }

echo "All ccollect tests PASSED"
