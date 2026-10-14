#!/bin/sh
# test_package/test_multimail.sh — consumer smoke test for multimail on OHOS.
#
# The installed `mm` binary is a purely interactive curses program
# (no --help/--version flags: any argv is treated as a packet path and
# the curses UI starts). The 6 checks below therefore validate the real
# packaged artifacts without driving the interactive UI:
#   1. bin/mm exists and is non-empty
#   2. readelf -h reports a valid ELF type (EXEC/DYN)
#   3. `strings mm` is non-empty and mentions MultiMail (non-empty-output
#      guard: proves the binary is real, not an empty-output false pass)
#   4. `strings mm` contains a packet-format token (QWK/SOUP/Blue Wave/OMEN)
#   5. share/man/man1/mm.1 exists, is non-empty and mentions MultiMail
#   6. headless execution negative control: run `mm` with stdin=/dev/null
#      and TERM=dumb under a shell watchdog; the curses UI cannot init
#      headless, so a fast non-zero exit proves the real binary executed
#      and that this harness observes exit codes (hang/timeout or rc=0
#      is a failure).
#
# HMBS hard-gate markers are printed at the end with real counters.
# Returns 0 on success, non-zero on first failure.
set -u

PASS=0
FAIL=0
DISCOVERED=6

# Writable scratch: OHOS /tmp is read-only (HMBS readonly_tmp). Never use
# /tmp: prefer HMBS-injected TMPDIR/TMP/TEMP only after a real touch probe
# ([ -w ] alone lies on read-only HMDFS), else fall back to the script dir.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRATCH_BASE="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ "$SCRATCH_BASE" = "/tmp" ] || [ "$SCRATCH_BASE" = "/tmp/" ]; then
    SCRATCH_BASE="$SCRIPT_DIR"
fi
if [ -n "$SCRATCH_BASE" ] && [ -d "$SCRATCH_BASE" ] 2>/dev/null; then
    if ! touch "$SCRATCH_BASE/.mm_wtest_$" 2>/dev/null; then
        SCRATCH_BASE="$SCRIPT_DIR"
    else
        rm -f "$SCRATCH_BASE/.mm_wtest_$"
    fi
else
    SCRATCH_BASE="$SCRIPT_DIR"
fi
SCRATCH="$(mktemp -d "${SCRATCH_BASE}/mm-test.XXXXXX" 2>/dev/null || echo "")"
if [ -z "$SCRATCH" ] || [ ! -d "$SCRATCH" ]; then
    SCRATCH="$SCRIPT_DIR/.scratch-$"
    mkdir -p "$SCRATCH"
fi
trap 'rm -rf "$SCRATCH"' EXIT INT TERM

assert_pass() {
    PASS=$((PASS + 1))
    echo "[PASS] $1"
}

assert_fail() {
    FAIL=$((FAIL + 1))
    if [ $# -ge 2 ] && [ -n "$2" ]; then
        echo "[FAIL] $1 — $2"
    else
        echo "[FAIL] $1"
    fi
}

# Locate the installed binary: prefer explicit MM_PKG_BIN dir (passed by
# test_package conanfile), then PATH lookup for bin/mm. Direct-path
# attempts tolerate HMDFS chmod=0 (missing +x): try chmod +x first,
# accept an existing regular file even if not +x yet.
echo "[test] PATH=$PATH"
echo "[test] MM_PKG_BIN=${MM_PKG_BIN:-(unset)}"
echo "[test] MM_PKG_DIR=${MM_PKG_DIR:-(unset)}"
if [ -n "${MM_PKG_BIN:-}" ]; then
    ls -l "${MM_PKG_BIN}" 2>&1 || true
fi
MM=""
if [ -n "${MM_PKG_BIN:-}" ] && [ -f "${MM_PKG_BIN}/mm" ]; then
    chmod +x "${MM_PKG_BIN}/mm" 2>/dev/null || true
    MM="${MM_PKG_BIN}/mm"
elif command -v mm >/dev/null 2>&1; then
    MM="$(command -v mm)"
fi
if [ -z "$MM" ]; then
    echo "[FAIL] bin/mm not found (MM_PKG_BIN nor PATH)"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test_multimail.sh","discovered":%d,"passedCount":0}\n' "$DISCOVERED"
    # shellcheck disable=SC2016
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"multimail 0.52 upstream has no test suite: no tests/ dir, no check/test target in the plain Makefile; make check has no rule"}'
    exit 1
fi
echo "[test] using binary: $MM"

# Locate the man page: prefer MM_PKG_DIR/share/man/man1/mm.1.
MAN=""
for _cand in "${MM_PKG_DIR:-}/share/man/man1/mm.1"; do
    if [ -n "${_cand:-}" ] && [ -f "$_cand" ]; then
        MAN="$_cand"
        break
    fi
done
echo "[test] using man page: ${MAN:-(none found)}"

# --- 1. binary exists and is non-empty ---
if [ -s "$MM" ]; then
    assert_pass "bin/mm exists and is non-empty"
else
    assert_fail "bin/mm missing or empty"
fi

# --- 2. ELF type (EXEC/DYN) ---
if command -v readelf >/dev/null 2>&1; then
    if readelf -h "$MM" >"$SCRATCH/mm_elf.out" 2>&1; then
        if grep -q "Type:" "$SCRATCH/mm_elf.out"; then
            elf_type=$(grep "Type:" "$SCRATCH/mm_elf.out" | head -1 | awk '{print $2}')
            if [ "$elf_type" = "EXEC" ] || [ "$elf_type" = "DYN" ]; then
                assert_pass "mm has valid ELF type ($elf_type)"
            else
                assert_fail "mm ELF type unexpected" "$elf_type"
            fi
        else
            assert_fail "readelf output missing Type" "$(head -c 300 "$SCRATCH/mm_elf.out")"
        fi
    else
        assert_fail "readelf -h failed on mm"
    fi
else
    assert_fail "readelf not available for ELF check"
fi

# --- 3. strings mention MultiMail (non-empty-output guard) ---
if command -v strings >/dev/null 2>&1; then
    if strings "$MM" >"$SCRATCH/mm_strings.out" 2>&1; then
        if [ -s "$SCRATCH/mm_strings.out" ] && grep -q "MultiMail" "$SCRATCH/mm_strings.out"; then
            assert_pass "strings mm mentions MultiMail"
        else
            assert_fail "strings mm missing MultiMail token" "$(head -c 300 "$SCRATCH/mm_strings.out")"
        fi
    else
        assert_fail "strings failed on mm"
    fi
else
    assert_fail "strings not available for binary check"
fi

# --- 4. packet-format token (QWK/SOUP/Blue Wave/OMEN) ---
if [ -f "$SCRATCH/mm_strings.out" ] && [ -s "$SCRATCH/mm_strings.out" ]; then
    if grep -qE "QWK|SOUP|Blue Wave|OMEN" "$SCRATCH/mm_strings.out"; then
        assert_pass "strings mm contains packet-format token"
    else
        assert_fail "strings mm missing packet-format token"
    fi
else
    assert_fail "strings output unavailable for format-token check"
fi

# --- 5. man page exists, non-empty, mentions MultiMail ---
if [ -n "$MAN" ] && [ -s "$MAN" ] && grep -q "MultiMail" "$MAN"; then
    assert_pass "mm.1 man page mentions MultiMail"
else
    assert_fail "mm.1 man page check failed" "$MAN"
fi

# --- 6. headless-execution negative control ---
# `mm` has no --help/--version: any invocation starts the curses UI.
# Headless (stdin=/dev/null, TERM=dumb) curses cannot init, so a fast
# non-zero exit proves the real binary executed and the harness observes
# exit codes. A hang (watchdog kill, rc=124) or rc=0 is a failure.
# No external `timeout` dependency: shell background + sleep watchdog.
if [ -n "${TERM:-}" ]; then
    OLD_TERM="$TERM"
else
    OLD_TERM=""
fi
TERM="dumb"
export TERM
"$MM" </dev/null >"$SCRATCH/mm_run.out" 2>&1 &
mm_pid=$!
slept=0
mm_rc=""
while kill -0 "$mm_pid" 2>/dev/null; do
    sleep 1
    slept=$((slept + 1))
    if [ "$slept" -ge 10 ]; then
        kill -9 "$mm_pid" 2>/dev/null || true
        wait "$mm_pid" 2>/dev/null || true
        mm_rc=124
        break
    fi
done
if [ -z "$mm_rc" ]; then
    wait "$mm_pid" 2>/dev/null
    mm_rc=$?
fi
if [ -n "$OLD_TERM" ]; then
    TERM="$OLD_TERM"
else
    unset TERM
fi
export TERM
echo "[test] headless run rc=$mm_rc output: $(head -c 300 "$SCRATCH/mm_run.out" 2>/dev/null)"
if [ "$mm_rc" = "124" ]; then
    assert_fail "mm headless run hung (watchdog kill)"
elif [ "$mm_rc" = "0" ]; then
    assert_fail "mm headless run unexpectedly exited 0"
elif [ -n "$mm_rc" ]; then
    assert_pass "mm headless run exits non-zero (rc=$mm_rc, curses needs a TTY)"
else
    assert_fail "mm headless run produced no exit code"
fi

# --- HMBS hard-gate markers (numbers come from the counters above) ---
passed="true"
if [ "$PASS" -ne "$DISCOVERED" ] || [ "$FAIL" -ne 0 ]; then
    passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"sh test_multimail.sh","discovered":%d,"passedCount":%d}\n' \
    "$passed" "$DISCOVERED" "$PASS"
# shellcheck disable=SC2016
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"make check","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"multimail 0.52 upstream has no test suite: no tests/ dir, no check/test target in the plain Makefile; make check has no rule"}'

echo "=== test_package summary: ${PASS}/${DISCOVERED} passed, ${FAIL} failed ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$DISCOVERED" ]; then
    exit 1
fi
exit 0
