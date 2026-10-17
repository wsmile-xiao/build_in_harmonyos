#!/bin/sh
# test_xwrited.sh — xwrited 3 consumer smoke test (6 real assertions).
# Usage: sh test_xwrited.sh <path-to-xwrited-binary> <workdir>
# Only deterministic paths are probed: --version/-V/--help/invalid-argument
# are all handled before any D-Bus/pty/notification setup, so the test needs
# no session bus and never hangs. A failing check keeps going so the RESULT
# trailer always reports real counts.
set -u

BIN="${1:-}"
WORKDIR="${2:-.}"

# HMBS readonly-/tmp compat: keep temp files in the injected writable dir.
_HMBS_TMP=""
for _cand in "${TMPDIR:-}" "${TMP:-}" "${TEMP:-}"; do
    if [ -n "${_cand:-}" ] && [ -d "$_cand" ] && [ -w "$_cand" ]; then
        _HMBS_TMP="$_cand"
        break
    fi
done
if [ -n "${_HMBS_TMP:-}" ]; then
    TMPDIR="$_HMBS_TMP"; TMP="$_HMBS_TMP"; TEMP="$_HMBS_TMP"
    export TMPDIR TMP TEMP
fi
mkdir -p "$WORKDIR" 2>/dev/null || true

PASS=0
FAIL=0

check_pass() {
    PASS=$((PASS + 1))
    echo "[PASS] $1"
}

check_fail() {
    FAIL=$((FAIL + 1))
    echo "[FAIL] $1"
}

echo "[test] xwrited consumer smoke test (bin=$BIN)"

# 1. Binary exists and is non-empty.
if [ -n "$BIN" ] && [ -f "$BIN" ] && [ -s "$BIN" ]; then
    check_pass "xwrited binary exists and is non-empty"
else
    check_fail "xwrited binary exists and is non-empty"
fi

# 2. aarch64 ELF (magic + e_machine == EM_AARCH64 == 183), read with od so no
# `file` command is required on the worker.
if [ -f "${BIN:-/nonexistent}" ]; then
    _magic="$(od -A n -t x1 -N 4 "$BIN" 2>/dev/null | tr -d ' \n')"
    _em="$(od -A n -t u2 -j 18 -N 2 "$BIN" 2>/dev/null | tr -d ' \n')"
    if [ "$_magic" = "7f454c46" ] && [ "$_em" = "183" ]; then
        check_pass "xwrited is an aarch64 ELF binary"
    else
        check_fail "xwrited is an aarch64 ELF binary (magic=$_magic em=$_em)"
    fi
else
    check_fail "xwrited is an aarch64 ELF binary (binary missing)"
fi

# 3. `xwrited --version` exits 0 and prints "xwrited 3".
if [ -f "${BIN:-/nonexistent}" ]; then
    _out="$("$BIN" --version 2>&1)"
    _rc=$?
    case "$_out" in
        *"xwrited 3"*)
            if [ "$_rc" -eq 0 ]; then
                check_pass "xwrited --version prints version and exits 0"
            else
                check_fail "xwrited --version prints version and exits 0 (rc=$_rc)"
            fi
            ;;
        *)
            check_fail "xwrited --version prints version and exits 0 (out=$_out rc=$_rc)"
            ;;
    esac
else
    check_fail "xwrited --version prints version and exits 0 (binary missing)"
fi

# 4. Short alias `-V` behaves the same.
if [ -f "${BIN:-/nonexistent}" ]; then
    _out="$("$BIN" -V 2>&1)"
    _rc=$?
    case "$_out" in
        *"xwrited 3"*)
            if [ "$_rc" -eq 0 ]; then
                check_pass "xwrited -V prints version and exits 0"
            else
                check_fail "xwrited -V prints version and exits 0 (rc=$_rc)"
            fi
            ;;
        *)
            check_fail "xwrited -V prints version and exits 0 (out=$_out rc=$_rc)"
            ;;
    esac
else
    check_fail "xwrited -V prints version and exits 0 (binary missing)"
fi

# 5. `--help` exits 0 and documents the version option (proves GApplication
# option handling runs).
if [ -f "${BIN:-/nonexistent}" ]; then
    _out="$("$BIN" --help 2>&1)"
    _rc=$?
    case "$_out" in
        *[Vv]ersion*)
            if [ "$_rc" -eq 0 ]; then
                check_pass "xwrited --help documents options and exits 0"
            else
                check_fail "xwrited --help documents options and exits 0 (rc=$_rc)"
            fi
            ;;
        *)
            check_fail "xwrited --help documents options and exits 0 (rc=$_rc)"
            ;;
    esac
else
    check_fail "xwrited --help documents options and exits 0 (binary missing)"
fi

# 6. Negative control: a positional argument is rejected before any bus/pty
# setup ("invalid argument", non-zero exit) — proves the harness observes
# real failures instead of silently passing.
if [ -f "${BIN:-/nonexistent}" ]; then
    _out="$("$BIN" ZZZ_INVALID_ARG_ZZZ 2>&1)"
    _rc=$?
    case "$_out" in
        *"invalid argument"*)
            if [ "$_rc" -ne 0 ]; then
                check_pass "xwrited rejects positional args with a diagnostic"
            else
                check_fail "xwrited rejects positional args with a diagnostic (rc=0)"
            fi
            ;;
        *)
            check_fail "xwrited rejects positional args with a diagnostic (out=$_out rc=$_rc)"
            ;;
    esac
else
    check_fail "xwrited rejects positional args with a diagnostic (binary missing)"
fi

echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ] && [ "$PASS" -gt 0 ]; then
    echo "[pass] xwrited smoke test passed"
    exit 0
else
    echo "[fail] xwrited smoke test failed"
    exit 1
fi
