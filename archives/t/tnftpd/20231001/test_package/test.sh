#!/bin/sh
# test_package/test.sh - consumer smoke test for tnftpd (FTP daemon).
# Usage: test.sh [bindir]
# BINDIR (argv $1) is authoritative, resolved by test_package/conanfile.py
# from tnftpd's package_folder.  tnftpd is a daemon with no --help/--version
# and blocks on the FTP loop with a live socket, so we assert:
#   (1) binary present   (2) binary executable   (3) ELF magic
#   (4) `-C <bogus-user>` access-check self-terminates cleanly (rc 0 or 1
#       == binary loads, parses args, runs sgetpwnam/checkaccess, no hang,
#       no signal).  All offline / deterministic.
# Emits HMBS machine-evidence markers (hard gate).  HMBS_UPSTREAM_TEST_RESULT
# is no_tests: tnftpd ships no upstream test framework (see MANIFEST.yml audit).
#
# OHOS readonly_tmp: /tmp is read-only (erofs) and /bin/sh materializes $()
# in hardcoded /tmp ignoring TMPDIR, so this script contains ZERO $(...)/`...`.
set -e

BINDIR="${1:-}"

# Seed a writable TMPDIR (parent already seeds; re-resolve for direct runs).
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

BIN=""
if [ -n "$BINDIR" ] && [ -f "$BINDIR/tnftpd" ]; then
    BIN="$BINDIR/tnftpd"
elif command -v tnftpd >/dev/null 2>&1; then
    command -v tnftpd >"$TMPDIR/tnftpd_path.txt" 2>/dev/null || true
    if read -r BIN <"$TMPDIR/tnftpd_path.txt" 2>/dev/null && [ -n "$BIN" ] && [ -f "$BIN" ]; then
        :
    else
        BIN="tnftpd"
    fi
fi

fail() {
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"tnftpd 20231001 ships no upstream test framework: no test directory, no TESTS/check target, no gtest bindings (see test_package/MANIFEST.yml upstream_test_audit).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh (presence/exec/ELF/-C self-terminate)","discovered":4,"passedCount":0}'
    exit 1
}

echo "[test] tnftpd binary resolution (bindir='${BINDIR:-}' bin='${BIN:-}')"
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "[test] FAIL: tnftpd binary not found"
    fail
fi

PASS_COUNT=0

# (1) binary present
echo "[test] check 1: binary present"
if [ -f "$BIN" ]; then
    echo "  PASS"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "  FAIL: $BIN missing"
fi

# (2) binary executable
echo "[test] check 2: binary executable"
if [ -x "$BIN" ]; then
    echo "  PASS"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "  FAIL: $BIN not executable"
fi

# (3) ELF magic (first 4 bytes = \177ELF) — byte-compare, no command substitution
echo "[test] check 3: ELF magic"
printf '\177ELF' >"$TMPDIR/elfmagic" 2>/dev/null || true
head -c 4 "$BIN" >"$TMPDIR/binfirst4" 2>/dev/null || true
if cmp -s "$TMPDIR/binfirst4" "$TMPDIR/elfmagic" 2>/dev/null; then
    echo "  PASS: $BIN is an ELF executable"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "  FAIL: $BIN is not an ELF binary (or head/cmp unavailable)"
fi

# (4) -C <bogus-user> access-check self-terminates cleanly (rc 0 or 1, no
# hang/signal).  NOTE: `tnftpd -C <bogus-user>` legitimately returns rc 1
# (access-check denies the unknown user), so the command MUST run inside an
# `if` condition instead of as a bare statement: `set -e` would otherwise
# abort the whole script on that non-zero return before `rc=$?` and the
# PASS/FAIL check could run (classic set -e capture gotcha).
echo "[test] check 4: 'tnftpd -C <bogus-user>' self-terminates"
if "$BIN" -C tnftpd-nosuch-user-0000 >"$TMPDIR/c_check.out" 2>&1; then
    rc=0
else
    rc=$?
fi
if [ "$rc" -eq 0 ] || [ "$rc" -eq 1 ]; then
    echo "  PASS: access-check exited rc=$rc (bogus user -> clean self-termination)"
    PASS_COUNT=$((PASS_COUNT+1))
else
    echo "  FAIL: access-check exited rc=$rc"
    echo "  c_check.out tail:"; tail -5 "$TMPDIR/c_check.out" 2>/dev/null || true
fi

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"tnftpd 20231001 ships no upstream test framework: no test directory, no TESTS/check target, no gtest bindings (see test_package/MANIFEST.yml upstream_test_audit).","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

if [ "$PASS_COUNT" -eq 4 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh (presence/exec/ELF/-C self-terminate)","discovered":4,"passedCount":4}'
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh (presence/exec/ELF/-C self-terminate)\",\"discovered\":4,\"passedCount\":$PASS_COUNT}"
    exit 1
fi
