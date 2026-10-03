#!/data/service/hnp/bin/bash
# test_package/test_vblade.sh — smoke test for vblade executable.
# Runs in conanrun env (PATH includes installed bin/).
# 4 deterministic cases, each increments PASS counter; marker counts
# come from that counter (single source, no stdout string counting).
set -eu

VBLADE_BIN=""
if [ -n "${1:-}" ] && [ -f "${1:-}" ]; then
    VBLADE_BIN="$1"
elif command -v vblade >/dev/null 2>&1; then
    VBLADE_BIN="$(command -v vblade)"
fi
if [ -z "$VBLADE_BIN" ] || [ ! -f "$VBLADE_BIN" ]; then
    echo "[fail] vblade binary not found (PATH=$PATH)"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test_vblade.sh\",\"discovered\":4,\"passedCount\":0}"
    exit 1
fi
chmod +x "$VBLADE_BIN" 2>/dev/null || true
echo "[test] vblade found at $VBLADE_BIN"

DISCOVERED=4
PASSED=0
LOGDIR="${TMPDIR:-.}"
TMPLOG="$LOGDIR/vblade_smoke.log"
touch "$TMPLOG" 2>/dev/null || TMPLOG="./vblade_smoke.log"

# TC-01: binary exists and is non-empty
if [ -s "$VBLADE_BIN" ]; then
    echo "[ok] TC-01 binary non-empty"
    PASSED=$((PASSED + 1))
else
    echo "[fail] TC-01 binary empty"
fi

# TC-02: ELF magic (7f 45 4c 46), read deterministically from the file itself
if od -A n -t x1 -N 4 "$VBLADE_BIN" 2>/dev/null | grep -q "7f 45 4c 46"; then
    echo "[ok] TC-02 ELF magic present"
    PASSED=$((PASSED + 1))
else
    echo "[fail] TC-02 not an ELF binary"
fi

# TC-03: no-arg invocation prints usage to stderr and exits 1 (real execution)
set +e
"$VBLADE_BIN" >"$TMPLOG" 2>&1
RC=$?
set -e
if [ $RC -eq 1 ] && [ -s "$TMPLOG" ] && grep -q "usage:" "$TMPLOG" && grep -q "shelf slot" "$TMPLOG"; then
    echo "[ok] TC-03 no-arg usage exit=1 with usage text"
    PASSED=$((PASSED + 1))
else
    echo "[fail] TC-03 unexpected no-arg behaviour (rc=$RC)"
    head -n 10 "$TMPLOG" 2>/dev/null || true
fi

# TC-04 (negative control): invalid option is rejected with usage (proves harness observes failures)
set +e
"$VBLADE_BIN" -Z >"$TMPLOG" 2>&1
RC2=$?
set -e
if [ $RC2 -ne 0 ] && [ -s "$TMPLOG" ] && grep -q "usage:" "$TMPLOG"; then
    echo "[ok] TC-04 invalid option rejected (rc=$RC2)"
    PASSED=$((PASSED + 1))
else
    echo "[fail] TC-04 invalid option not rejected (rc=$RC2)"
    head -n 10 "$TMPLOG" 2>/dev/null || true
fi

if [ "$PASSED" -eq "$DISCOVERED" ]; then
    RESULT_TRUE=true
else
    RESULT_TRUE=false
fi
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$RESULT_TRUE,\"command\":\"bash test_vblade.sh\",\"discovered\":$DISCOVERED,\"passedCount\":$PASSED}"
if [ "$PASSED" -eq "$DISCOVERED" ]; then
    echo "[pass] vblade smoke test passed ($PASSED/$DISCOVERED)"
else
    echo "[fail] vblade smoke test failed ($PASSED/$DISCOVERED)"
    exit 1
fi
