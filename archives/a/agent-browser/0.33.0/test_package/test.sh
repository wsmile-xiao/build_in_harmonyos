#!/bin/sh
# test_package/test.sh — smoke test for agent-browser executable
# Runs in conanrun env (PATH includes installed bin/)
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
set -uo pipefail

PASS=0
FAIL=0

# cd to a writable directory (HMBS TMPDIR; OHOS /tmp is read-only)
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"

echo "[test] agent-browser --version"
VERSION_OUT=$(agent-browser --version 2>&1)
if printf '%s' "$VERSION_OUT" | grep -q "agent-browser 0.33.0"; then
    PASS=$((PASS + 1))
    echo "[ok] --version prints 'agent-browser 0.33.0'"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --version output unexpected: $VERSION_OUT"
fi

echo "[test] agent-browser --help"
HELP_OUT=$(agent-browser --help 2>&1)
if printf '%s' "$HELP_OUT" | grep -qi "usage"; then
    PASS=$((PASS + 1))
    echo "[ok] --help shows Usage section"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --help output unexpected: $HELP_OUT"
fi

echo "[test] agent-browser doctor --offline --quick --json"
DOCTOR_OUT=$(agent-browser doctor --offline --quick --json 2>&1)
RC=$?
# 上游 doctor 语义：无 Chrome 等环境缺失时返回 rc=1 属合法结果
# （cli/tests/doctor_cli.rs 断言 rc==0 || rc==1 均有效）。消费者断言
# 验证输出为合法 JSON 且含 checks 数组与 summary 字段。
if { [ "$RC" -eq 0 ] || [ "$RC" -eq 1 ]; } && \
   printf '%s' "$DOCTOR_OUT" | grep -q '"checks"' && \
   printf '%s' "$DOCTOR_OUT" | grep -q '"summary"'; then
    PASS=$((PASS + 1))
    echo "[ok] offline doctor emits JSON payload (rc=$RC)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] offline doctor rc=$RC output: $DOCTOR_OUT"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":3,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
