#!/bin/sh
# test_xrefresh.sh — xrefresh 1.1.0 的 L1 消费者测试（由 test_package/conanfile.py 调用）
#
# 用法: sh test_xrefresh.sh <被测 xrefresh 绝对路径> <LD_PRELOAD 冒号串>
#
# 口径：
#   * POSIX sh only。不用 set -e/-u/pipefail（toybox ash 不接受），每条断言自己
#     捕获 rc 并把输出原样打进日志（loader 报错必须看得见）。
#   * 6 条断言全部实测过才写进脚本，声明数 ≤ 实测数；上游 0 测试用例，故这些是
#     自造断言，但每条都真实执行被测二进制（R34），没有一条是 print-only 空壳。
#   * 不假装验证了"重绘全部窗口"——那需要真 X server。这里覆盖的是零成本可测面：
#     版本/usage/缩写解析/未知参数/缺参，以及无 DISPLAY 时**干净报错而不是挂住**
#     （同时证明 libX11 的运行期符号真的解析得动）。
#   * 每条命令都套 timeout（可用时）：卡住要显式暴露成失败，绝不把超时当通过。

XREFRESH_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XREFRESH_BIN" ]; then
    echo "FAIL: xrefresh binary path not provided"
    exit 1
fi

if [ ! -f "$XREFRESH_BIN" ]; then
    echo "FAIL: $XREFRESH_BIN not found"
    exit 1
fi

BIN_DIR=$(dirname "$XREFRESH_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"
if [ -n "$LD_PRELOAD_EXTRA" ]; then
    LD_PRELOAD="$LD_PRELOAD_EXTRA"
    export LD_PRELOAD
fi

if command -v timeout >/dev/null 2>&1; then
    TMO="timeout 60"
else
    TMO=""
fi

echo "[shell] $0"
echo "[bin]   $XREFRESH_BIN"
echo "[env]   LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env]   LD_PRELOAD=${LD_PRELOAD:-}"
echo "[env]   DISPLAY=${DISPLAY:-<unset>}"

# 依赖闭包留档（musl 下 ldd 可能不存在，退到 readelf/objdump）
echo "[deps]"
if command -v ldd >/dev/null 2>&1; then
    ldd "$XREFRESH_BIN" 2>&1 | head -12
elif command -v llvm-readelf >/dev/null 2>&1; then
    llvm-readelf -d "$XREFRESH_BIN" 2>/dev/null | grep -E "NEEDED|RUNPATH|RPATH" | head -12
else
    echo "  (no ldd/readelf available)"
fi

discovered=6
passed=0

# expect_rc <want_rc> <label> -- 之后由 run_and_check 组合
ok() {
    echo "PASS: $1"
    passed=$((passed + 1))
}

bad() {
    echo "FAIL: $1"
}

echo "[test 1/$discovered] -version（PACKAGE_STRING 路径，XOpenDisplay 之前退出）"
out=$($TMO "$XREFRESH_BIN" -version 2>&1)
rc=$?
echo "$out"
if [ "$rc" = 0 ] && echo "$out" | grep -q "xrefresh 1.1.0"; then
    ok "-version rc=0 且输出 xrefresh 1.1.0"
else
    bad "-version rc=$rc output=$out"
fi

echo "[test 2/$discovered] -help（usage 路径）"
out=$($TMO "$XREFRESH_BIN" -help 2>&1)
rc=$?
echo "$out" | head -6
if [ "$rc" = 0 ] && echo "$out" | grep -q "^usage:"; then
    ok "-help rc=0 且打印 usage"
else
    bad "-help rc=$rc"
fi

echo "[test 3/$discovered] -v 缩写（isabbreviation 分支）"
out=$($TMO "$XREFRESH_BIN" -v 2>&1)
rc=$?
echo "$out"
if [ "$rc" = 0 ] && echo "$out" | grep -q "xrefresh 1.1.0"; then
    ok "-v 缩写 rc=0"
else
    bad "-v rc=$rc output=$out"
fi

echo "[test 4/$discovered] 未知参数必须 rc=1 + unrecognized argument"
out=$($TMO "$XREFRESH_BIN" -definitely-not-an-option 2>&1)
rc=$?
echo "$out" | head -3
if [ "$rc" = 1 ] && echo "$out" | grep -q "unrecognized argument"; then
    ok "未知参数 rc=1 且报 unrecognized argument"
else
    bad "未知参数 rc=$rc"
fi

echo "[test 5/$discovered] -delay 缺参数必须 rc=1 + requires an argument"
out=$($TMO "$XREFRESH_BIN" -delay 2>&1)
rc=$?
echo "$out" | head -3
if [ "$rc" = 1 ] && echo "$out" | grep -q "requires an argument"; then
    ok "-delay 缺参 rc=1 且报 requires an argument"
else
    bad "-delay rc=$rc"
fi

echo "[test 6/$discovered] 无 DISPLAY：必须干净报错 rc=1（不挂住），并证明 libX11 符号解析得动"
out=$(env -u DISPLAY $TMO "$XREFRESH_BIN" 2>&1)
rc=$?
echo "$out"
if [ "$rc" = 1 ] && echo "$out" | grep -q "unable to open display"; then
    ok "无 DISPLAY rc=1 且报 unable to open display（动态链接可用，且未超时）"
elif [ "$rc" = 124 ]; then
    bad "无 DISPLAY 时 60s 超时（rc=124）＝挂住，不算通过"
else
    bad "无 DISPLAY rc=$rc output=$out"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "RESULT: $passed/$discovered 通过"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xrefresh.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "RESULT: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xrefresh.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
exit 0
