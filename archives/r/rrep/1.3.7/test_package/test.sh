#!/bin/sh
# test_package/test.sh - HarmonyOS functional consumer test for rrep 1.3.7.
# Usage: test.sh [bindir]
#
# BINDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the rrep package_folder.
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs), and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output capture uses plain redirections into $TMPDIR files + grep checks.
#
# Upstream test audit: rrep 1.3.7 ships NO test suite (602-entry tarball
# audited: no tests/ or test/ directory, no *test* source files except
# m4/progtest.m4 autoconf macro, no TESTS/check_PROGRAMS in any Makefile.am,
# no AC_CONFIG_TESTDIR in configure.ac; SUBDIRS = lib src po doc).
# `make check` is an automake no-op. See test_package/MANIFEST.yml.
#
# All seven cases below are NEW HarmonyOS functional consumer cases: they
# actually execute the packaged OHOS binary and verify observable behaviour
# (version/help output, stdin filtering, file replacement, dry-run,
# ignore-case, recursive), not mere file existence.
set -u

BINDIR="${1:-}"

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
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"rrep-1.3.7.tar.gz audited (sha256 6179798a5e86833c455cf3e5f65ce6cc35f6d3888f47d74de8346e1bfa211fcd, 602 entries): no tests/ or test/ directory, no test source files (only m4/progtest.m4 autoconf macro), no TESTS/check_PROGRAMS in Makefile.am, no AC_CONFIG_TESTDIR in configure.ac (SUBDIRS = lib src po doc), so make check is an automake no-op."}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":7,"passedCount":0}'
    exit 1
}

echo "[test] rrep consumer functional test (bindir='${BINDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    echo "[test] FAIL: bindir not resolved"
    fail
fi

if [ ! -x "$BINDIR/rrep" ]; then
    echo "[test] FAIL: $BINDIR/rrep missing or not executable"
    ls -la "$BINDIR" 2>&1 || true
    fail
fi
echo "[test] bindir listing:"
ls -la "$BINDIR" 2>&1 || true

# ---------------------------------------------------------------- case 1
# Version banner: proves configure-time PACKAGE_STRING substitution survived.
echo "[test] case 1: rrep_version_banner"
"$BINDIR/rrep" --version >"$TMPDIR/c1.out" 2>"$TMPDIR/c1.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "rrep 1.3.7" "$TMPDIR/c1.out" 2>/dev/null; then
    echo "ok: rrep_version_banner (rc=0, 'rrep 1.3.7' on stdout)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_version_banner (rc=$RC, expected rc=0 + 'rrep 1.3.7')"
    cat "$TMPDIR/c1.out" "$TMPDIR/c1.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 2
# Help output: exercises the real option table (messages.c print_help).
echo "[test] case 2: rrep_help_output"
"$BINDIR/rrep" --help >"$TMPDIR/c2.out" 2>"$TMPDIR/c2.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "Usage" "$TMPDIR/c2.out" 2>/dev/null \
   && grep -q "PATTERN" "$TMPDIR/c2.out" 2>/dev/null; then
    echo "ok: rrep_help_output (rc=0, Usage + PATTERN)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_help_output (rc=$RC, expected Usage + PATTERN)"
    cat "$TMPDIR/c2.out" "$TMPDIR/c2.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# Stdin filter: no FILE means stdin->stdout (replace_string path).
echo "[test] case 3: rrep_stdin_filter"
printf 'hello foo\nsecond foo line\n' > "$TMPDIR/c3.in"
"$BINDIR/rrep" -F foo bar <"$TMPDIR/c3.in" >"$TMPDIR/c3.out" 2>"$TMPDIR/c3.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "hello bar" "$TMPDIR/c3.out" 2>/dev/null \
   && grep -q "second bar line" "$TMPDIR/c3.out" 2>/dev/null; then
    echo "ok: rrep_stdin_filter (rc=0, both lines replaced)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_stdin_filter (rc=$RC, expected both lines replaced)"
    cat "$TMPDIR/c3.out" "$TMPDIR/c3.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 4
# File replace: fixed-string mode rewrites the file in place.
echo "[test] case 4: rrep_file_replace"
printf 'hello foo world\nfoo foo\n' > "$TMPDIR/c4.txt"
"$BINDIR/rrep" -F foo bar "$TMPDIR/c4.txt" >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "hello bar world" "$TMPDIR/c4.txt" 2>/dev/null \
   && grep -q "bar bar" "$TMPDIR/c4.txt" 2>/dev/null; then
    echo "ok: rrep_file_replace (rc=0, file rewritten)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_file_replace (rc=$RC, expected file rewritten)"
    cat "$TMPDIR/c4.txt" "$TMPDIR/c4.out" "$TMPDIR/c4.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 5
# Dry-run: simulation mode must leave the file untouched.
echo "[test] case 5: rrep_dry_run"
printf 'hello foo world\n' > "$TMPDIR/c5.txt"
"$BINDIR/rrep" --dry-run -F foo bar "$TMPDIR/c5.txt" >"$TMPDIR/c5.out" 2>"$TMPDIR/c5.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "hello foo world" "$TMPDIR/c5.txt" 2>/dev/null; then
    echo "ok: rrep_dry_run (rc=0, file untouched)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_dry_run (rc=$RC, expected file untouched)"
    cat "$TMPDIR/c5.txt" "$TMPDIR/c5.out" "$TMPDIR/c5.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 6
# Ignore-case: -i folds case distinctions (REG_ICASE regex path).
# NOTE: -i only affects regex matching (regcomp REG_ICASE); the OPT_FIXED
# branch in src/pattern.c match_pattern() uses case-sensitive strstr()
# and ignores -i, so -i combined with -F can never match FOO for foo.
# Use regex mode (no -F) here.
echo "[test] case 6: rrep_ignore_case"
printf 'Hello FOO World\n' > "$TMPDIR/c6.txt"
"$BINDIR/rrep" -i foo bar "$TMPDIR/c6.txt" >"$TMPDIR/c6.out" 2>"$TMPDIR/c6.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "Hello bar World" "$TMPDIR/c6.txt" 2>/dev/null; then
    echo "ok: rrep_ignore_case (rc=0, case folded)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_ignore_case (rc=$RC, expected case folded)"
    cat "$TMPDIR/c6.txt" "$TMPDIR/c6.out" "$TMPDIR/c6.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 7
# Recursive: -r processes directories (fts/exclude path).
echo "[test] case 7: rrep_recursive"
mkdir -p "$TMPDIR/c7dir/sub" 2>/dev/null || true
printf 'foo one\n' > "$TMPDIR/c7dir/a.txt"
printf 'foo two\n' > "$TMPDIR/c7dir/sub/b.txt"
"$BINDIR/rrep" -r -F foo bar "$TMPDIR/c7dir" >"$TMPDIR/c7.out" 2>"$TMPDIR/c7.err"
RC=$?
if [ "$RC" -eq 0 ] && grep -q "bar one" "$TMPDIR/c7dir/a.txt" 2>/dev/null \
   && grep -q "bar two" "$TMPDIR/c7dir/sub/b.txt" 2>/dev/null; then
    echo "ok: rrep_recursive (rc=0, both files replaced)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: rrep_recursive (rc=$RC, expected both files replaced)"
    cat "$TMPDIR/c7dir/a.txt" "$TMPDIR/c7dir/sub/b.txt" "$TMPDIR/c7.out" "$TMPDIR/c7.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"rrep-1.3.7.tar.gz audited (sha256 6179798a5e86833c455cf3e5f65ce6cc35f6d3888f47d74de8346e1bfa211fcd, 602 entries): no tests/ or test/ directory, no test source files (only m4/progtest.m4 autoconf macro), no TESTS/check_PROGRAMS in Makefile.am, no AC_CONFIG_TESTDIR in configure.ac (SUBDIRS = lib src po doc), so make check is an automake no-op."}'

echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of 7)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq 7 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":7,"passedCount":7}'
    exit 0
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":7,"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi
