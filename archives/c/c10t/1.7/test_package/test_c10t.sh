#!/bin/sh
# test_c10t.sh — consumer functional test for the c10t 1.7 package.
# Runs the installed bin/c10t binary through 4 real invocations and prints
# a machine-readable "RESULT: P passed, F failed" trailer line, which
# test_package/conanfile.py parses into HMBS_TEST_PACKAGE_RESULT.
# Case 4 is a negative control (no arguments must fail), proving the
# harness observes real failures instead of passing empty output.

set -u

BIN="${C10T_BIN:-c10t}"
# Device /tmp is read-only: prefer the HMBS-injected writable TMPDIR/TMP/TEMP,
# fall back to the current directory (never to hardcoded /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
OUT="$_TMPBASE/c10t-test-out.txt"
PASS=0
FAIL=0

report() {
    # $1 = case number, $2 = ok (0/1), $3 = label
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    # $1 = exit code; print bounded output excerpt for diagnosis.
    # (Keeps failures actionable: exit code alone cannot distinguish a
    # loader failure from an app error.)
    echo "  exit=$1, output excerpt (first 10 lines):"
    head -n 10 "$OUT" 2>/dev/null || echo "  (no output file)"
}

# Case 1: --help exits 0 and prints usage.
"$BIN" --help > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    if grep -qi "usage" "$OUT"; then
        report 1 0 "--help prints usage"
    else
        dump_out $rc
        report 1 1 "--help printed no usage text"
    fi
else
    dump_out $rc
    report 1 1 "--help exited $rc"
fi

# Case 2: --list-colors exits 0 with non-empty block color output
# (this is also the Homebrew formula's own test).
"$BIN" --list-colors > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    if [ -s "$OUT" ]; then
        report 2 0 "--list-colors lists block colors"
    else
        dump_out $rc
        report 2 1 "--list-colors produced empty output"
    fi
else
    dump_out $rc
    report 2 1 "--list-colors exited $rc"
fi

# Case 3: --version exits 0 and reports 1.7.
"$BIN" --version > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    if grep -q "1\\.7" "$OUT"; then
        report 3 0 "--version reports 1.7"
    else
        dump_out $rc
        report 3 1 "--version output lacks 1.7"
    fi
else
    dump_out $rc
    report 3 1 "--version exited $rc"
fi

# Case 4 (negative control): bare invocation must fail with the genuine app
# usage error ("No action specified, please type `c10t -h' for help",
# src/main.cpp exit_error path). The pattern is deliberately the exact app
# message: the previous lax "usage|error|require" pattern also matched the
# musl loader's "Error loading shared library ..." line, so a binary that
# never reached main() spuriously passed this control.
"$BIN" > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
    dump_out $rc
    report 4 1 "bare invocation unexpectedly succeeded"
else
    if grep -qi "no action specified" "$OUT"; then
        report 4 0 "bare invocation fails with usage error"
    else
        dump_out $rc
        report 4 1 "bare invocation failed without app usage error (exit=$rc)"
    fi
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
