#!/bin/sh
# test_package/test.sh - HarmonyOS consumer smoke test for vamps 0.99.2.
# Usage: test.sh [bindir]
#
# BINDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the vamps package_folder.
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs), and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output capture uses plain redirections into $TMPDIR files + grep checks.
#
# Upstream test audit: vamps 0.99.2 ships NO upstream test framework
# (no test/tests directory, no check/TESTS target in any Makefile, no
# gtest/pytest/criterion bindings - see test_package/MANIFEST.yml).  All
# five cases below are NEW HarmonyOS consumer test cases proving the
# packaged OHOS binaries actually execute on this platform.
set -u

BINDIR="${1:-}"

# HMBS readonly_tmp: prefer the injected writable TMPDIR/TMP/TEMP for any
# temp files.  Re-resolve here in case the script is invoked directly.
# NOTE: no $(...) below on purpose; use $PWD, not $(pwd).
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

PASS_COUNT=0
FAIL_COUNT=0

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"vamps 0.99.2 ships no upstream test framework: no test/tests directory, no check/TESTS target in any Makefile, no gtest/pytest/criterion bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":5,"passedCount":0}'
    exit 1
}

echo "[test] vamps consumer smoke test (bindir='${BINDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "[test] FAIL: bindir not resolved"
    fail
fi

if [ ! -x "$BINDIR/vamps" ]; then
    echo "[test] FAIL: $BINDIR/vamps missing or not executable"
    ls -la "$BINDIR" 2>&1 || true
    fail
fi
if [ ! -x "$BINDIR/play_cell" ]; then
    echo "[test] FAIL: $BINDIR/play_cell missing or not executable"
    ls -la "$BINDIR" 2>&1 || true
    fail
fi
echo "[test] bindir listing:"
ls -la "$BINDIR" 2>&1 || true

# ---------------------------------------------------------------- case 1
# vamps rejects an unknown long option: getopt_long_only ('?' path, musl
# getopt.h) → usage() on stderr → exit 1.
echo "[test] case 1: vamps_usage_bogus_option"
"$BINDIR/vamps" --bogus </dev/null >"$TMPDIR/c1.out" 2>"$TMPDIR/c1.err"
RC=$?
if [ "$RC" -eq 1 ] && grep -q "Usage: vamps" "$TMPDIR/c1.err" 2>/dev/null; then
    echo "ok: vamps_usage_bogus_option (rc=1, usage printed to stderr)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: vamps_usage_bogus_option (rc=$RC, expected rc=1 + 'Usage: vamps' on stderr)"
    cat "$TMPDIR/c1.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 2
# vamps with no -S and stdin not a regular file: musl fstat(0)+S_ISREG
# guard → explicit message + usage() → exit 1.
echo "[test] case 2: vamps_usage_stdin_not_regular"
"$BINDIR/vamps" </dev/null >"$TMPDIR/c2.out" 2>"$TMPDIR/c2.err"
RC=$?
if [ "$RC" -eq 1 ] && grep -q "Standard input is not a regular file" "$TMPDIR/c2.err" 2>/dev/null; then
    echo "ok: vamps_usage_stdin_not_regular (rc=1, fstat guard works on OHOS musl)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: vamps_usage_stdin_not_regular (rc=$RC, expected rc=1 + fstat guard message)"
    cat "$TMPDIR/c2.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# vamps -e with a non-numeric factor: getopt_long_only + strtof validation
# ("Bad factor") → usage() → exit 1.
echo "[test] case 3: vamps_usage_bad_factor"
"$BINDIR/vamps" -e notanumber </dev/null >"$TMPDIR/c3.out" 2>"$TMPDIR/c3.err"
RC=$?
if [ "$RC" -eq 1 ] && grep -q "Bad factor" "$TMPDIR/c3.err" 2>/dev/null; then
    echo "ok: vamps_usage_bad_factor (rc=1, strtof validation works)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: vamps_usage_bad_factor (rc=$RC, expected rc=1 + 'Bad factor')"
    cat "$TMPDIR/c3.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 4
# play_cell with fewer than 4 positional args: usage() → exit 1 BEFORE any
# DVD device access.  Proves the play_cell binary (the libdvdread consumer,
# statically linked against libdvdread.a) actually loads and runs on OHOS
# (a broken dependency link would die with rc=127 "shared library not found").
echo "[test] case 4: play_cell_usage_no_args"
"$BINDIR/play_cell" </dev/null >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
RC=$?
if [ "$RC" -eq 1 ] && grep -q "Usage: play_cell" "$TMPDIR/c4.err" 2>/dev/null; then
    echo "ok: play_cell_usage_no_args (rc=1, binary loads incl. static libdvdread)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: play_cell_usage_no_args (rc=$RC, expected rc=1 + 'Usage: play_cell')"
    cat "$TMPDIR/c4.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 5
# Functional requantizer pipeline smoke: empty regular-file PS input with
# -e 1.0 -S 1 → vamps allocates its video buffers, starts the pthread
# reader/writer pipeline, hits immediate EOF in vap_leader()'s
# while(!lock(SECT_SIZE)) and shuts down cleanly (rc=0, no Fatal).
echo "[test] case 5: vamps_requant_empty_ps_eof"
: > "$TMPDIR/empty.ps"
"$BINDIR/vamps" -e 1.0 -S 1 <"$TMPDIR/empty.ps" >"$TMPDIR/c5.out" 2>"$TMPDIR/c5.err"
RC=$?
if [ "$RC" -eq 0 ] && ! grep -q "Fatal" "$TMPDIR/c5.err" 2>/dev/null; then
    echo "ok: vamps_requant_empty_ps_eof (rc=0, pthread pipeline + clean EOF shutdown)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: vamps_requant_empty_ps_eof (rc=$RC, expected rc=0 clean EOF shutdown)"
    cat "$TMPDIR/c5.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"vamps 0.99.2 ships no upstream test framework: no test/tests directory, no check/TESTS target in any Makefile, no gtest/pytest/criterion bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of 5)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq 5 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":5,"passedCount":5}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":5,"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi
