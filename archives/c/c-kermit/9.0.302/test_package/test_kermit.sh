#!/data/service/hnp/bin/bash
# test_kermit.sh — c-kermit 9.0.302 consumer smoke test.
# Really executes the packaged `kermit` binary (R34: the binary IS the API).
set -u

BIN="kermit"
discovered=3
passed=0
failed=0

echo "[test] $BIN exists and is executable"
if command -v "$BIN" >/dev/null 2>&1 && [ -x "$(command -v "$BIN")" ]; then
    passed=$((passed + 1))
    echo "[OK] $BIN found at $(command -v "$BIN")"
else
    failed=$((failed + 1))
    echo "[FAIL] $BIN not on PATH"
fi

echo "[test] $BIN --version prints 9.0.302"
VOUT=$("$BIN" --version </dev/null 2>&1)
VRC=$?
echo "$VOUT" | head -n 5
if echo "$VOUT" | grep -q "9\.0\.302"; then
    passed=$((passed + 1))
    echo "[OK] version banner contains 9.0.302 (rc=$VRC)"
else
    failed=$((failed + 1))
    echo "[FAIL] version banner missing 9.0.302 (rc=$VRC)"
fi

echo "[test] $BIN runs its command parser (quit)"
QOUT=$(printf 'quit\n' | "$BIN" 2>&1)
QRC=$?
echo "$QOUT" | head -n 5
if [ "$QRC" -eq 0 ]; then
    passed=$((passed + 1))
    echo "[OK] quit path exits 0"
else
    failed=$((failed + 1))
    echo "[FAIL] quit path rc=$QRC"
fi

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_kermit.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_kermit.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"makefile","command":"make linux (no test target)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"c-kermit 9.0.302 上游无测试套件：cku302.tar.gz 仅 74 个顶层文件（makefile + 约 60 个 .c/.h + 文档），无 tests/ 或 test/ 目录；makefile 共 676 个目标全部为平台构建目标（linux/linuxa/xermit/wermit 等），无 check/test 目标、无 TESTS 变量；构建不使用 autoconf/CMake，无测试宏"}\n'
exit 0
