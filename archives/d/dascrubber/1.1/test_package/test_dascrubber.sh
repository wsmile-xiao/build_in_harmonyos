#!/bin/sh
# test_dascrubber.sh — consumer functional test for the dascrubber 1.1 package.
# Runs the installed bin/ tools through real invocations and prints
# a machine-readable "RESULT: P passed, F failed" trailer line, which
# test_package/conanfile.py parses into HMBS_TEST_PACKAGE_RESULT and
# HMBS_UPSTREAM_TEST_RESULT (upstream ships no formal suite, so these
# Usage/error-contract executions are the executable upstream-equivalent
# verification required by the HMBS executed>0 gate).
# Case 1 is the binary inventory; cases 2-11 are negative controls (bare
# invocation must fail with the genuine app "Usage:" contract); the exact
# "Usage:" match proves the harness observes real app failures instead of
# loader errors or empty output (c10t/toybox-tar lessons).

set -u

BIN_DIR="${DASCRUBBER_BIN_DIR:-/usr/local/bin}"
# Device /tmp is read-only: prefer the HMBS-injected writable TMPDIR/TMP/TEMP,
# fall back to the current directory (never to hardcoded /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
OUT="$_TMPBASE/dascrubber-test-out.txt"
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
    echo "  exit=$1, output excerpt (first 10 lines):"
    head -n 10 "$OUT" 2>/dev/null || echo "  (no output file)"
}

check_usage_contract() {
    # $1 = case number, $2 = binary path, $3 = label
    _bin="$2"
    _label="$3"
    "$_bin" > "$OUT" 2>&1
    rc=$?
    if [ $rc -eq 0 ]; then
        dump_out $rc
        report "$1" 1 "$_label unexpectedly succeeded"
        return
    fi
    # Genuine app contract: usage line contains "Usage:" plus output non-empty.
    # The musl loader's "Error loading shared library ..." cannot match this.
    # All 10 tools print "Usage: <Prog> ..." to stderr via ARG_INIT and exit 1
    # when required <source:db>/<overlaps:las> args are missing (verified in
    # DAScover.c/DASqv.c/DAStrim.c/DASpatch.c/DASedit.c/DASmap.c/DASrealign.c/
    # REPcover.c/REPqv.c/REPtrim.c mains).
    if grep -q "Usage:" "$OUT" && [ -s "$OUT" ]; then
        report "$1" 0 "$_label fails with Usage contract"
    else
        dump_out $rc
        report "$1" 1 "$_label failed without Usage contract (exit=$rc)"
    fi
}

# Case 1: all 10 binaries present, executable, non-empty.
_missing=0
_empty=0
for t in DAScover DASqv DAStrim DASpatch DASedit DASmap DASrealign REPcover REPqv REPtrim; do
    if [ ! -x "$BIN_DIR/$t" ]; then
        echo "  missing/not-executable: $BIN_DIR/$t"
        _missing=$((_missing + 1))
    elif [ ! -s "$BIN_DIR/$t" ]; then
        echo "  empty binary: $BIN_DIR/$t"
        _empty=$((_empty + 1))
    fi
done
if [ "$_missing" -eq 0 ] && [ "$_empty" -eq 0 ]; then
    report 1 0 "all 10 dascrubber binaries present and non-empty"
else
    report 1 1 "binary inventory failed (missing=$_missing empty=$_empty)"
fi

# Cases 2-11: usage-contract negative controls, one per shipped binary.
check_usage_contract 2 "$BIN_DIR/DAScover" "DAScover bare invocation"
check_usage_contract 3 "$BIN_DIR/DASqv" "DASqv bare invocation"
check_usage_contract 4 "$BIN_DIR/DAStrim" "DAStrim bare invocation"
check_usage_contract 5 "$BIN_DIR/DASpatch" "DASpatch bare invocation"
check_usage_contract 6 "$BIN_DIR/DASedit" "DASedit bare invocation"
check_usage_contract 7 "$BIN_DIR/DASmap" "DASmap bare invocation"
check_usage_contract 8 "$BIN_DIR/DASrealign" "DASrealign bare invocation"
check_usage_contract 9 "$BIN_DIR/REPcover" "REPcover bare invocation"
check_usage_contract 10 "$BIN_DIR/REPqv" "REPqv bare invocation"
check_usage_contract 11 "$BIN_DIR/REPtrim" "REPtrim bare invocation"

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
