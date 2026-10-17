#!/data/service/hnp/bin/bash
# test_package/test.sh — functional tests for endlessh executable
# Runs in conanrun env (PATH includes installed bin/)
#
# Upstream (endlessh 1.1) ships NO test suite — no test target in Makefile,
# no test files, no CI. These tests supplement that gap with binary-level
# assertions on documented CLI behavior.
set -eu

# Use the test_package build dir (writable) for temp files — /tmp is read-only on OHOS.
TMPD="${ENDLESSH_TEST_TMPD:-$(pwd)}"
export ENDLESSSH_TEST_TMPD="$TMPD"

PASS=0
FAIL=0
TOTAL=0

ok()   { echo "✅ $1"; PASS=$((PASS+1)); }
fail() { echo "❌ $1"; FAIL=$((FAIL+1)); }

echo "─── endlessh 1.1 test suite ($TOTAL planned) ───"

# Test 1: -h prints help to stdout and exits 0
echo "[test] endlessh -h (help, exit 0)"
if endlessh -h >$TMPD/esh_h.out 2>$TMPD/esh_h.err; then
    if grep -q "Usage: endlessh" $TMPD/esh_h.out && grep -q -- "-h" $TMPD/esh_h.out; then
        ok "endlessh -h prints usage to stdout"
    else
        fail "endlessh -h output missing usage text"
    fi
else
    fail "endlessh -h should exit 0"
fi
TOTAL=$((TOTAL+1))
rm -f $TMPD/esh_h.out $TMPD/esh_h.err

# Test 2: -V prints version and exits 0
echo "[test] endlessh -V (version, exit 0)"
if endlessh -V >$TMPD/esh_v.out 2>&1; then
    if grep -q "1.1" $TMPD/esh_v.out; then
        ok "endlessh -V prints version containing '1.1'"
    else
        fail "endlessh -V output missing version"
    fi
else
    fail "endlessh -V should exit 0"
fi
TOTAL=$((TOTAL+1))
rm -f $TMPD/esh_v.out

# Test 3: invalid option exits non-zero
echo "[test] endlessh -z (invalid option, exit !=0)"
if ! endlessh -z >/dev/null 2>&1; then
    ok "endlessh -z rejected with non-zero exit"
else
    fail "endlessh -z should exit non-zero"
fi
TOTAL=$((TOTAL+1))

# Test 4: -d with out-of-range value exits non-zero
echo "[test] endlessh -d -1 (invalid delay, exit !=0)"
if ! endlessh -d -1 >/dev/null 2>&1; then
    ok "endlessh -d -1 rejected with non-zero exit"
else
    fail "endlessh -d -1 should exit non-zero"
fi
TOTAL=$((TOTAL+1))

# Test 5: daemon mode binds a high port, prints diagnostics, exits 0 on timeout
echo "[test] endlessh -v -p 65531 (daemon bind + diagnostics)"
OUT=$(timeout 2 endlessh -v -p 65531 2>&1 || true)
if echo "$OUT" | grep -q "Port 65531" && echo "$OUT" | grep -q "Delay"; then
    ok "endlessh daemon logs Port and Delay diagnostics"
else
    fail "endlessh daemon diagnostics missing Port/Delay"
fi
TOTAL=$((TOTAL+1))

echo "─── results: $PASS/$TOTAL passed, $FAIL failed ───"
[ "$FAIL" -eq 0 ] || exit 1
