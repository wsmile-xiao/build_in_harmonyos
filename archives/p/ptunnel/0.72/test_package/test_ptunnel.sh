#!/bin/sh
# test_ptunnel.sh — ptunnel 0.72 consumer smoke test
#
# ptunnel has no upstream test suite (see MANIFEST.yml), so this test verifies
# the packaged binary is present, executable, and functionally responsive:
#   check 1: bin/ptunnel exists and is executable
#   check 2: invoking it with `-h` prints the version/usage banner and exits
#            non-zero (proves dynamic runtime deps resolve and the binary is a
#            real ptunnel; full tunneling requires root + a capture device +
#            live ICMP, not available in a build-test sandbox)
#
# Exits 0 iff every check passes; prints one deterministic `RESULT:` summary
# line (the sole source of passed/failed counts for the build harness).

set -u

BIN_DIR="$1"
PTUNNEL="$BIN_DIR/ptunnel"

pass_count=0
fail_count=0
run_count=0

check_pass() {
    pass_count=$((pass_count + 1))
    run_count=$((run_count + 1))
    printf 'PASS: %s\n' "$1"
}

check_fail() {
    fail_count=$((fail_count + 1))
    run_count=$((run_count + 1))
    printf 'FAIL: %s\n' "$1"
}

# --- check 1: binary present + executable ---
if [ -x "$PTUNNEL" ]; then
    check_pass "ptunnel binary present and executable at $PTUNNEL"
else
    check_fail "ptunnel binary missing or not executable at $PTUNNEL"
fi

# --- check 2: -h prints banner and exits non-zero ---
if [ -x "$PTUNNEL" ]; then
    out="$("$PTUNNEL" -h 2>&1)"
    rc=$?
    if [ "$rc" -ne 0 ] && printf '%s\n' "$out" | grep -q "Usage:" \
            && printf '%s\n' "$out" | grep -q "ptunnel v"; then
        check_pass "-h prints 'Usage:' + 'ptunnel v' banner and exits $rc (non-zero)"
    else
        check_fail "-h expected 'Usage:' + 'ptunnel v' banner and non-zero exit, got rc=$rc"
    fi
fi

printf 'RESULT: %s passed, %s failed\n' "$pass_count" "$fail_count"

# HMBS 机器证据标记：单行、独立 JSON 对象，值只含标记自身的五个字段。
# discovered=真实执行用例数（run_count，由 check_pass/check_fail 计数，非
# 硬编码），passedCount=通过数（pass_count）。二者来自本脚本确定性的计数器，
# 不做字符串数数/算术修补；恒等式 passed+failed==executed==discovered 恒成立。
if [ "$fail_count" -eq 0 ]; then
    TEST_PKG_PASSED=true
else
    TEST_PKG_PASSED=false
fi
printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":${TEST_PKG_PASSED},\"command\":\"test_ptunnel.sh <pkg_bin>\",\"discovered\":${run_count},\"passedCount\":${pass_count}}"

[ "$fail_count" -eq 0 ]
