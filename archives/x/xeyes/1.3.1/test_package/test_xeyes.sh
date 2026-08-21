#!/bin/sh
# test_xeyes.sh — verify xeyes binary works on HarmonyOS
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged xeyes binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#       (prebuilt-stack libX11.so.6 needs libxcb.so.1/libXau.so.6 at runtime;
#        HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#        the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh, do not
# hardcode /data/service/hnp/bin/bash; xidle already-passed test is the same
# pattern). No set -e/-u/pipefail: toybox ash rejects them; every assertion
# captures its own rc and always prints output so loader errors hit the log.
#
# 真机演进（第 4 轮根因确认）：bash 5.3.0 能正常执行 ELF，127 的真正原因是
# 预编译栈 libX11.so.6 的 DT_NEEDED（libxcb.so.1/libXau.so.6）在设备上只有
# .a 没有 .so。CI #28097 起主配方 libX11/libXext 改自 conan 依赖
# （libx11/6.4.0 + libxext/6.4.0），不再依赖预编译栈；本脚本通过 $2 的
# LD_PRELOAD（libXau → libXdmcp → libxcb → libX11 → libXext 依赖序）和
# conanrun 环境注入的 LD_LIBRARY_PATH（各依赖包 libdir）双重保证运行时寻库。

XEYES_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$XEYES_BIN" ]; then
    echo "FAIL: xeyes binary path not provided"
    exit 1
fi

if [ ! -x "$XEYES_BIN" ]; then
    echo "FAIL: $XEYES_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$XEYES_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

discovered=2
passed=0

# 诊断：musl ldd 会打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$XEYES_BIN" 2>&1 || true
fi

echo "[test 1/$discovered] xeyes -version"
version_output=$("$XEYES_BIN" -version 2>&1)
rc=$?
echo "$version_output"
if [ $rc -ne 0 ]; then
    echo "FAIL: xeyes -version exit=$rc"
else
    # xeyes -version 打印 PACKAGE_STRING（"xeyes 1.3.1"）并在 XtAppInitialize
    # 之前 exit(0)（xeyes.c main()），无需 X server
    if echo "$version_output" | grep -q "xeyes 1.3.1"; then
        echo "PASS: xeyes -version reports xeyes 1.3.1"
        passed=$((passed + 1))
    else
        echo "FAIL: unexpected xeyes -version output"
    fi
fi

echo "[test 2/$discovered] xeyes -help"
help_output=$("$XEYES_BIN" -help 2>&1)
rc=$?
if [ $rc -ne 0 ]; then
    echo "FAIL: xeyes -help exit=$rc"
else
    echo "PASS: xeyes -help exit=0"
    passed=$((passed + 1))
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_xeyes.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_xeyes.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
