#!/data/service/hnp/bin/bash
# test_xsel.sh — xsel 1.2.1 消费者冒烟测试
# 真实执行打包的 xsel 二进制（R34：二进制即被测 API）。
# xsel 的 --version / --help 在 XOpenDisplay 之前就 exit(0)，
# 因此无 X server 的 headless 环境也能验证可执行性与输出正确性。
set -u

BIN="xsel"
discovered=3
passed=0
failed=0

echo "[test] $BIN --version"
VOUT=$("$BIN" --version 2>&1)
VRC=$?
echo "$VOUT"
if [ "$VRC" -eq 0 ] && echo "$VOUT" | grep -q "xsel version 1.2.1"; then
    passed=$((passed + 1))
    echo "[OK] --version prints version line"
else
    failed=$((failed + 1))
    echo "[FAIL] --version rc=$VRC, expected 'xsel version 1.2.1' in output"
fi

echo "[test] $BIN --help"
HOUT=$("$BIN" --help 2>&1)
HRC=$?
if [ "$HRC" -eq 0 ] && echo "$HOUT" | grep -q "Usage: xsel"; then
    passed=$((passed + 1))
    echo "[OK] --help prints usage"
else
    failed=$((failed + 1))
    echo "[FAIL] --help rc=$HRC, expected 'Usage: xsel' in output"
fi

echo "[test] $BIN --output (无 X server → 优雅失败，验证 X11 代码路径真实可达)"
OOUT=$("$BIN" --output -t 500 2>&1)
ORC=$?
echo "$OOUT"
case "$ORC" in
    0)
        failed=$((failed + 1))
        echo "[FAIL] --output unexpectedly succeeded (X server present?)"
        ;;
    *)
        passed=$((passed + 1))
        echo "[OK] --output fails gracefully without X server (rc=$ORC)"
        ;;
esac

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xsel.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xsel.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"autotools","command":"make check (n/a)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"xsel 1.2.1 上游无测试套件：GitHub tag archive 无 tests/ 目录；Makefile.am 仅 bin_PROGRAMS=xsel 与 dist_man_MANS=xsel.1x，无 check/test 目标、无 TESTS 变量；configure.ac 仅做编译/头文件/函数探测与 PKG_CHECK_MODULES([X],[x11])，无测试宏"}\n'
exit 0
