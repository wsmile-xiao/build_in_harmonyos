#!/bin/sh
# test_package/test.sh — HarmonyOS consumer test suite for qalc 5.11.0.
#
# Usage: test.sh <bindir> <datadir>
#
# Runs on the real HarmonyOS worker (cross-built binaries cannot execute on
# the macOS dev box).  Contents:
#   U1-U17  the complete upstream batch suite (17 files, 688 input->expected
#           cases), executed by qalc's own `--test-file` runner.  The batch
#           and csv files are copied verbatim from the release tarball.
#   H1-H3   HarmonyOS-specific runtime checks:
#           H1 packaged definitions load + unit conversion ("5 m to cm")
#           H2 non-interactive expression evaluation exit code ("1 + 2 * 6")
#           H3 musl libm trig evaluation ("sin(pi/2)")
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output is captured with plain redirections into $TMPDIR files and asserted
# with grep.
set -u

BINDIR="${1:-}"
DATADIR="${2:-}"

case "$0" in
    */*) SCRIPT_DIR="${0%/*}" ;;
    *) SCRIPT_DIR="." ;;
esac

if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/qalc" ]; then
    echo "[test] ABORT: $BINDIR/qalc missing or not executable"
    exit 1
fi
if [ -z "$DATADIR" ] || [ ! -f "$DATADIR/functions.xml" ]; then
    echo "[test] ABORT: definitions dir not resolved (functions.xml missing)"
    exit 1
fi
export QALCULATE_DEFINITIONS_DIR="$DATADIR"

SEC="$BINDIR/qalc"

TOTAL_FILES=17
TOTAL_CASES=688
FILES_PASSED=0
FILES_FAILED=0
CASES_PASSED=0
H_PASS=0
H_FAIL=0

emit_markers() {
    # No $(...) command substitution: OHOS /bin/sh materializes it in the
    # read-only /tmp, so status strings are computed with plain conditionals.
    UP_STATUS="pass"
    PKG_PASSED="true"
    if [ "$FILES_FAILED" -ne 0 ]; then UP_STATUS="fail"; fi
    if [ "$FILES_FAILED" -ne 0 ] || [ "$H_FAIL" -ne 0 ]; then PKG_PASSED="false"; fi
    echo "HMBS_UPSTREAM_TEST_RESULT={\"status\":\"$UP_STATUS\",\"framework\":\"qalc --test-file\",\"command\":\"qalc --test-file tests/*.batch\",\"files_discovered\":17,\"files_passed\":$FILES_PASSED,\"discovered\":688,\"passed\":$CASES_PASSED,\"failed\":$((TOTAL_CASES-CASES_PASSED))}"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":\"$PKG_PASSED\",\"command\":\"/bin/sh test.sh\",\"discovered\":20,\"passedCount\":$((FILES_PASSED+H_PASS))}"
}

run_batch() {
    fname="$1"
    cases="$2"
    echo "[test] upstream suite: $fname ($cases cases)"
    # Absolute path: qalc is invoked from tests/' parent dir (stats.batch
    # loads tests/vectordata.csv relative to the current directory).
    "$SEC" --test-file="$SCRIPT_DIR/tests/$fname" >"$TMPDIR/qalc-batch.out" 2>"$TMPDIR/qalc-batch.err"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "ok: U:$fname ($cases cases, rc=0)"
        FILES_PASSED=$((FILES_PASSED+1))
        CASES_PASSED=$((CASES_PASSED+cases))
    else
        echo "FAIL: U:$fname (rc=$rc)"
        echo "--- output ---"
        cat "$TMPDIR/qalc-batch.out" 2>/dev/null || true
        echo "--- stderr ---"
        cat "$TMPDIR/qalc-batch.err" 2>/dev/null || true
        FILES_FAILED=$((FILES_FAILED+1))
    fi
}

# ------------------------------------------------------------------ H1
echo "[test] case H1: harmonyos_definitions_and_unit_conversion"
"$SEC" "5 m to cm" >"$TMPDIR/h1.out" 2>"$TMPDIR/h1.err"
H1_RC=$?
if [ "$H1_RC" -eq 0 ] && grep -q '500' "$TMPDIR/h1.out"; then
    echo "ok: H1 harmonyos_definitions_and_unit_conversion (rc=0, 5 m to cm -> 500 cm)"
    H_PASS=$((H_PASS+1))
else
    echo "FAIL: H1 harmonyos_definitions_and_unit_conversion (rc=$H1_RC, expected 500 in output)"
    cat "$TMPDIR/h1.out" "$TMPDIR/h1.err" 2>/dev/null || true
    H_FAIL=$((H_FAIL+1))
fi

# ------------------------------------------------------------------ H2
echo "[test] case H2: harmonyos_expression_exit_code"
"$SEC" "1 + 2 * 6" >"$TMPDIR/h2.out" 2>"$TMPDIR/h2.err"
H2_RC=$?
if [ "$H2_RC" -eq 0 ] && grep -q '13' "$TMPDIR/h2.out"; then
    echo "ok: H2 harmonyos_expression_exit_code (rc=0, 1 + 2 * 6 = 13)"
    H_PASS=$((H_PASS+1))
else
    echo "FAIL: H2 harmonyos_expression_exit_code (rc=$H2_RC, expected 13 in output)"
    cat "$TMPDIR/h2.out" "$TMPDIR/h2.err" 2>/dev/null || true
    H_FAIL=$((H_FAIL+1))
fi

# ------------------------------------------------------------------ H3
echo "[test] case H3: harmonyos_musl_libm_trig"
"$SEC" "sin(pi/2)" >"$TMPDIR/h3.out" 2>"$TMPDIR/h3.err"
H3_RC=$?
if [ "$H3_RC" -eq 0 ] && grep -q '= 1' "$TMPDIR/h3.out"; then
    echo "ok: H3 harmonyos_musl_libm_trig (rc=0, sin(pi/2) = 1)"
    H_PASS=$((H_PASS+1))
else
    echo "FAIL: H3 harmonyos_musl_libm_trig (rc=$H3_RC, expected '= 1' in output)"
    cat "$TMPDIR/h3.out" "$TMPDIR/h3.err" 2>/dev/null || true
    H_FAIL=$((H_FAIL+1))
fi

# ------------------------------------------------------- upstream suite
cd "$SCRIPT_DIR" || { echo "[test] ABORT: cannot enter script dir"; exit 1; }

run_batch bitwise.batch 24
run_batch calculus.batch 11
run_batch dates.batch 11
run_batch explog.batch 10
run_batch geometry.batch 30
run_batch limits.batch 198
run_batch matrixvector.batch 131
run_batch numberbase.batch 15
run_batch operators.batch 30
run_batch parser.batch 27
run_batch percentages.batch 29
run_batch polynomial.batch 49
run_batch solver.batch 36
run_batch stats.batch 39
run_batch strings.batch 24
run_batch units.batch 13
run_batch variables.batch 11

emit_markers
echo "[test] summary: upstream_files=$FILES_PASSED/$TOTAL_FILES upstream_cases=$CASES_PASSED/$TOTAL_CASES harmony=$H_PASS/3 fail_files=$FILES_FAILED harmony_fail=$H_FAIL"
if [ "$FILES_FAILED" -eq 0 ] && [ "$H_FAIL" -eq 0 ]; then
    exit 0
fi
exit 1
