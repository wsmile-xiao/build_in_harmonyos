#!/bin/sh
# test_xev.sh — verify xev binary works on HarmonyOS (headless, no X server)
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xev binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#        (xev links libXrandr/libX11 whose DT_NEEDED closure — libXext,
#         libXrender, libxcb, libXau, libXdmcp — must resolve at load time;
#         HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#         the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh, do not
# hardcode /data/service/hnp/bin/bash; xeyes/xidle already-passed tests are the
# same pattern). No set -e/-u/pipefail: toybox ash rejects them; every
# assertion captures its own rc and always prints output so loader errors hit
# the log.
#
# 全部断言只走 xev.c 中早于 XOpenDisplay 的命令行路径（-version/--version/
# -help/非法选项），故无 X server 也能真实执行被测二进制（R34）。

XEV_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XEV_BIN" ]; then
    echo "FAIL: xev binary path not provided"
    exit 1
fi

if [ ! -x "$XEV_BIN" ]; then
    echo "FAIL: $XEV_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$XEV_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

discovered=4
passed=0

# 诊断：ldd 打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XEV_BIN" 2>&1 || true
fi

# --- test 1: xev -version (xev.c case 'v': puts(PACKAGE_STRING); exit(0)) ---
echo "[test 1/$discovered] xev -version"
out=$("$XEV_BIN" -version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xev -version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xev 1.2.7"; then
    echo "PASS: xev -version reports 'xev 1.2.7' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xev -version unexpected output (no 'xev 1.2.7')"
fi

# --- test 2: xev --version (xev.c case '-': puts(PACKAGE_STRING); exit(0)) ---
echo "[test 2/$discovered] xev --version"
out=$("$XEV_BIN" --version 2>&1)
rc=$?
echo "$out"
if [ $rc -ne 0 ]; then
    echo "FAIL: xev --version exit=$rc (expected 0)"
elif echo "$out" | grep -q "xev 1.2.7"; then
    echo "PASS: xev --version reports 'xev 1.2.7' (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xev --version unexpected output (no 'xev 1.2.7')"
fi

# --- test 3: xev -help (xev.c case 'h': usage(NULL, EXIT_SUCCESS)) ---
# usage() 打印 "usage:  <progname> [-options ...]" 与选项表到 stderr，exit 0。
echo "[test 3/$discovered] xev -help"
out=$("$XEV_BIN" -help 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -ne 0 ]; then
    echo "FAIL: xev -help exit=$rc (expected 0)"
elif echo "$out" | grep -qi "usage:"; then
    echo "PASS: xev -help prints usage banner (exit 0)"
    passed=$((passed + 1))
else
    echo "FAIL: xev -help missing usage banner"
fi

# --- test 4: 非法选项走 usage(NULL, EXIT_FAILURE) ---
# xev 对未识别选项以非 0 退出并打印 usage（区别于会打开 display 的正常路径），
# 验证参数解析的错误分支被执行。
echo "[test 4/$discovered] xev -Zz (unrecognized option -> nonzero exit)"
out=$("$XEV_BIN" -Zz 2>&1)
rc=$?
echo "$out" | head -20
if [ $rc -eq 0 ]; then
    echo "FAIL: xev -Zz exit=0 (expected nonzero for unrecognized option)"
elif echo "$out" | grep -qi "usage:"; then
    echo "PASS: xev -Zz rejected with usage + nonzero exit (rc=$rc)"
    passed=$((passed + 1))
else
    echo "FAIL: xev -Zz nonzero exit but no usage banner (rc=$rc)"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xev.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xev.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
