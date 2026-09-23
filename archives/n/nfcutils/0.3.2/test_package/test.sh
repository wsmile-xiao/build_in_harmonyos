#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the lsnfc executable
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary.
#
# lsnfc 在无 NFC 硬件环境的真实行为（上游 src/lsnfc.c 源码实证）：
#   nfc_list_devices() 返回 0 → 打印 "ERROR: No device found." →
#   走完 main 尾部 nfc_exit() 后 return EXIT_SUCCESS（退出码 0）。
# 因此断言：输出含 "No device found" 且退出码为 0、不阻塞（timeout 保护）。
set -euo pipefail

DISCOVERED=0
PASSED=0
RUN_OUTPUT=""
RUN_STATUS=0

run_lsnfc() {
    set +e
    RUN_OUTPUT="$(timeout 10 lsnfc 2>&1)"
    RUN_STATUS=$?
    set -e
}

# Test 1: lsnfc binary is present and executable
DISCOVERED=$((DISCOVERED + 1))
if command -v lsnfc >/dev/null 2>&1 && [ -x "$(command -v lsnfc)" ]; then
    echo "OK: lsnfc binary found in PATH"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: lsnfc binary not found in PATH"
fi

# Test 2: headless (no NFC hardware) run reports "No device found" with rc=0
DISCOVERED=$((DISCOVERED + 1))
run_lsnfc
OUT="$RUN_OUTPUT"
RC="$RUN_STATUS"
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -qi "No device found"; then
    echo "OK: lsnfc reports 'No device found' in headless env (rc=$RC)"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: lsnfc did not report 'No device found' (rc=$RC, output: $OUT)"
fi

# Test 3: output is non-empty (the tool really executed)
DISCOVERED=$((DISCOVERED + 1))
if [ -n "$OUT" ]; then
    echo "OK: lsnfc produced non-empty output"
    PASSED=$((PASSED + 1))
else
    echo "FAIL: lsnfc produced no output"
fi

echo "test_package: ${PASSED}/${DISCOVERED} checks passed"

# ── HMBS 机器证据标记（真实用例计数，由上面实际执行产生）──
if [ "$PASSED" -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED"
# 上游无测试（已审计 0.3.2 归档仅 lsnfc.c 单源码 + Makefile，无 check/test 目标）
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"audited nfcutils-0.3.2.tar.gz: single lsnfc.c source + Makefile.am bin_PROGRAMS only, no test framework or make check target"}\n'

[ "$PASSED" -eq "$DISCOVERED" ] || exit 1