#!/bin/sh
# test_xprop.sh — verify xprop binary works on HarmonyOS
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xprop binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#       (conan libX11.so.6 needs libxcb.so.1/libXau.so.6 at runtime;
#        HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#        the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh, do not
# hardcode /data/service/hnp/bin/bash; xidle/xeyes already-passed tests are
# the same pattern). No set -e/-u/pipefail: toybox ash rejects them; every
# assertion captures its own rc and always prints output so loader errors
# hit the log.
#
# ★ 实测口径（first-build 记录，见 notes.md）：xprop 与 xeyes(Xt) 不同，
#   main 在解析任何参数（含 -version/-root）之前先经 dsimple.c Open_Display
#   连接 X server —— dsimple.c L106 XOpenDisplay(NULL) 失败后 fprintf
#   "unable to open display ''" 并 exit(1)。因此本平台（无 X server）两项
#   断言均走上游确定性 no-X 错误路径：真实执行被测二进制（动态链接/签名/
#   进入 main/上游错误路径全链路，R34 实质依赖被测包），不冒充功能级
#   真机验证（not_covered 如实记账，见 MANIFEST.yml）。

XPROP_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XPROP_BIN" ]; then
    echo "FAIL: xprop binary path not provided"
    exit 1
fi

if [ ! -x "$XPROP_BIN" ]; then
    echo "FAIL: $XPROP_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$XPROP_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

# 上游确定性 no-X 错误路径断言体：rc=1（dsimple.c exit(1)）且错误文本为
# dsimple.c L105-107 的 "unable to open display"。
no_x_path() {
    _out=$(env -u DISPLAY -u XAUTHORITY "$@" 2>&1)
    _rc=$?
    echo "$_out"
    if [ "$_rc" -eq 1 ] && echo "$_out" | grep -q "unable to open display"; then
        return 0
    fi
    return 1
}

discovered=2
passed=0

echo "[test 1/$discovered] xprop -version under no-X env (real exec + upstream Open_Display error path, dsimple.c L106)"
if no_x_path "$XPROP_BIN" -version; then
    echo "PASS: xprop -version exits 1 with upstream 'unable to open display'"
    passed=$((passed + 1))
else
    echo "FAIL: xprop -version did not take the upstream no-X error path (expect rc=1 + 'unable to open display')"
fi

echo "[test 2/$discovered] xprop -root under no-X env (main query entry, same deterministic path)"
if no_x_path "$XPROP_BIN" -root; then
    echo "PASS: xprop -root exits 1 with upstream 'unable to open display'"
    passed=$((passed + 1))
else
    echo "FAIL: xprop -root did not take the upstream no-X error path"
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xprop.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xprop.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
