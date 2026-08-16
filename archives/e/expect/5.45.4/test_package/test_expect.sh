#!/data/service/hnp/bin/bash
# test_package/test_expect.sh — smoke test for expect/5.45.4
#
# Tests:
#   1. expect binary exists and is executable
#   2. expect can execute a simple script (puts "hello")
#   3. expect spawn echo works
#   4. EXP_STTY=/bin/true does not cause failure
#
# Must exit non-zero on any failure.

set -euo pipefail

EXPECT_BIN="${EXPECT_BIN:-expect}"
PASS_COUNT=0
FAIL_COUNT=0
TOTAL=0

pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "        [ok] $1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "        [fail] $1"; }
check_result() { TOTAL=$((TOTAL + 1)); if [ "$1" -eq 0 ]; then pass "$2"; else fail "$2"; fi; }

echo "[test] expect/5.45.4 smoke test suite"
echo ""

echo "  TEST 1: expect binary is executable"
TOTAL=$((TOTAL + 1))
if command -v "$EXPECT_BIN" >/dev/null 2>&1; then
    pass "expect binary found at $(command -v "$EXPECT_BIN")"
else
    fail "expect binary not found in PATH"
fi

echo "  TEST 2: expect can execute a simple script"
TOTAL=$((TOTAL + 1))
RESULT=$(EXP_STTY=/bin/true "$EXPECT_BIN" -c 'puts "hello from expect"' 2>/dev/null)
if [ "$RESULT" = "hello from expect" ]; then
    pass "expect -c 'puts ...' works"
else
    fail "unexpected output: $RESULT"
fi

echo "  TEST 3: expect spawn echo"
TOTAL=$((TOTAL + 1))
EXP_STTY=/bin/true "$EXPECT_BIN" -c '
set timeout 10
spawn echo spawn_echo_test
expect { "spawn_echo_test" { exit 0 } timeout { exit 1 } }
expect eof
' >/dev/null 2>&1 && pass "spawn echo works" || fail "spawn echo failed"

echo "  TEST 4: EXP_STTY=/bin/true does not cause failure"
TOTAL=$((TOTAL + 1))
EXP_STTY=/bin/true "$EXPECT_BIN" -c '
set timeout 5
spawn echo stty_test
expect eof
' >/dev/null 2>&1 && pass "EXP_STTY=/bin/true works" || fail "EXP_STTY=/bin/true caused failure"

echo ""
echo "----------------------------------------"
echo "  Results: $PASS_COUNT/$TOTAL passed, $FAIL_COUNT failed"
echo "----------------------------------------"
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "  FAIL: Some tests did not pass."
    exit 1
fi
echo "  PASS: All smoke tests passed."
exit 0
