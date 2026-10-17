#!/bin/sh
# test_package/test.sh — HarmonyOS consumer smoke test for yasr 0.6.9.
# Usage: test.sh [bindir] [package_folder]
#
# BINDIR (argv $1) and PKGDIR (argv $2) are authoritative: resolved by
# test_package/conanfile.py from the yasr package_folder, so nothing here
# depends on PATH or on a hard-coded install prefix (PACKAGE_DATA_DIR is
# compiled in by configure from --prefix, which under Conan is the package
# folder itself).
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# /bin/sh materialises $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) and ZERO backticks;
# output is captured with plain redirections into $TMPDIR files + grep.
#
# Upstream test audit (authority: test_package/MANIFEST.yml): yasr 0.6.9 ships
# NO upstream test harness — no test/tests directory, no TESTS/check_PROGRAMS
# in any Makefile.am, no gtest/criterion/check bindings.  The single
# program-ish automake entry is `noinst_PROGRAMS = keytest`, an interactive
# keyboard diagnostic that make check never runs.  All five cases below are
# therefore NEW HarmonyOS consumer cases proving the packaged OHOS binary
# really loads and behaves on this platform.
set -u

BINDIR="${1:-}"
PKGDIR="${2:-}"

# Number of consumer cases defined below.  Kept in one variable and asserted
# against the actual tally at the end, so the reported denominator can never
# drift from what really ran.
DISCOVERED=5

# ---------------------------------------------------------------- writable tmp
# HMBS readonly_tmp: prefer the injected writable TMPDIR/TMP/TEMP.  No $(...)
# anywhere below on purpose (use $PWD, not $(pwd)).
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
export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR" TEMPDIR="$TMPDIR"

# config.c builds the ~/.yasr.conf candidate with an unconditional
# sprintf(..., getenv("HOME"), ...), so HOME must be non-NULL for yasr to reach
# its -C lookup at all.  Seed it with the writable tmp dir if the harness has
# none (never overrides a real HOME).
if [ -z "${HOME:-}" ] || [ ! -d "${HOME:-/nonexistent}" ]; then
    HOME="$TMPDIR"
    export HOME
fi

PASS_COUNT=0
FAIL_COUNT=0

# Emit the upstream-audit marker with the tally we actually produced, then fail.
bail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"yasr 0.6.9 ships no upstream test framework: no TESTS/check_PROGRAMS in any Makefile.am, no test directory, no gtest/criterion/check bindings (noinst_PROGRAMS = keytest is an interactive diagnostic, not a test).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":'"$DISCOVERED"',"passedCount":'"$PASS_COUNT"'}'
    exit 1
}

echo "[test] yasr consumer smoke test (bindir='${BINDIR:-}' pkgdir='${PKGDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ] || [ -z "$PKGDIR" ] || [ ! -d "$PKGDIR" ]; then
    echo "[test] FAIL: bindir/pkgdir not resolved"
    bail
fi

YASR="$BINDIR/yasr"
CONF="$PKGDIR/share/yasr/yasr.conf"
MAN="$PKGDIR/share/man/man1/yasr.1"

# ---------------------------------------------------------------- case 1
# The packaged binary exists, is a regular file (not a dangling symlink —
# SONAME/symlink hygiene) and carries the exec bit.  Also proves cpp_info
# bindirs = ["bin"] matches what package() actually installed.
echo "[test] case 1: packaged_binary_present_executable"
if [ -f "$YASR" ] && [ ! -L "$YASR" ] && [ -x "$YASR" ]; then
    ls -l "$YASR" 2>&1 || true
    echo "ok: bin/yasr is a regular executable file"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: bin/yasr missing, symlinked, or not executable"
    ls -la "$BINDIR" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 2
# The upstream default configuration must ship with the package: config.c's
# third lookup candidate is PACKAGE_DATA_DIR/yasr.conf, and Makefile.am
# installs pkgdata_DATA = yasr.conf.  Non-empty check kills a truncated install.
echo "[test] case 2: packaged_default_config_installed"
if [ -f "$CONF" ] && [ -s "$CONF" ]; then
    wc -c "$CONF" 2>&1 || true
    echo "ok: share/yasr/yasr.conf installed and non-empty"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: share/yasr/yasr.conf missing or empty"
    ls -la "$PKGDIR/share" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 3
# man1_MANS = yasr.1 must land in the package (documents the -C/-c/-s/-p CLI
# surface this test relies on).
echo "[test] case 3: man_page_installed"
if [ -f "$MAN" ] && [ -s "$MAN" ]; then
    wc -c "$MAN" 2>&1 || true
    echo "ok: share/man/man1/yasr.1 installed"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: share/man/man1/yasr.1 missing"
    ls -la "$PKGDIR/share/man/man1" 2>&1 || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 4
# Negative path: with -C pointing at a non-existent file, yasr prints its
# three-candidate search list and exits non-zero.  Reaching that message at all
# proves the OHOS ELF loaded (a broken dynamic link would exit 127 without any
# program output) and that getopt processing works under musl.
# Note: yasr writes this diagnostic with printf() -> stdout.
echo "[test] case 4: missing_config_reported_with_rc_nonzero"
"$YASR" -C "$TMPDIR/no-such-yasr.conf" </dev/null \
    >"$TMPDIR/c4.out" 2>"$TMPDIR/c4.err"
RC=$?
if [ "$RC" -ne 0 ] && grep -q "unable to find" "$TMPDIR/c4.out" 2>/dev/null; then
    echo "ok: yasr -C <missing> -> rc=$RC and printed the config search list"
    head -3 "$TMPDIR/c4.out" 2>&1 || true
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: yasr -C <missing> -> rc=$RC, expected non-zero + 'unable to find'"
    cat "$TMPDIR/c4.out" "$TMPDIR/c4.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# ---------------------------------------------------------------- case 5
# Positive path: hand yasr the packaged default configuration.  It then parses
# it, opens a pty, spawns the requested program inside it, hits immediate EOF on
# /dev/null stdin and shuts the session down cleanly (rc=0, no diagnostic).
# This is the real functional exercise of the openpty()/forkpty() code path that
# patch 0004 had to unblock — the pty session is created through the OHOS musl
# libutil implementations, not through yasr's bundled BSD replacements (LIBOBJS
# is empty on this target).
echo "[test] case 5: pty_session_with_packaged_config"
"$YASR" -C "$CONF" </dev/null >"$TMPDIR/c5.out" 2>"$TMPDIR/c5.err"
RC=$?
if [ "$RC" -eq 0 ] && ! grep -q "unable to find" "$TMPDIR/c5.out" 2>/dev/null; then
    echo "ok: yasr -C <packaged yasr.conf> -> rc=0, config accepted, pty session ended cleanly"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "FAIL: yasr -C <packaged conf> -> rc=$RC, expected 0 and no 'unable to find'"
    cat "$TMPDIR/c5.out" "$TMPDIR/c5.err" 2>/dev/null || true
    FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"yasr 0.6.9 ships no upstream test framework: no TESTS/check_PROGRAMS in any Makefile.am, no test directory, no gtest/criterion/check bindings (noinst_PROGRAMS = keytest is an interactive diagnostic, not a test).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of $DISCOVERED)"

if [ "$FAIL_COUNT" -ne 0 ] || [ "$PASS_COUNT" -ne "$DISCOVERED" ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":'"$DISCOVERED"',"passedCount":'"$PASS_COUNT"'}'
    exit 1
fi

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":'"$DISCOVERED"',"passedCount":'"$DISCOVERED"'}'
exit 0
