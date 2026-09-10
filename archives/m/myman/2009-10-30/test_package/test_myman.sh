#!/bin/sh
# test_myman.sh — verify myman binary works on HarmonyOS
# Called by test_package/conanfile.py test() with:
#   $1 = absolute path to the packaged myman binary
#   $2 = optional colon-joined LD_PRELOAD list of runtime .so paths
#       (conan libx11/libxext 运行期 DT_NEEDED 需要 libxcb.so.1/libXau.so.6；
#        HMBS [stale_runtime_library]: loader may ignore LD_LIBRARY_PATH, so
#        the recipe passes absolute paths to preload as a fallback).
#
# POSIX sh only (HMBS [shell_getcwd]: run with injected SHELL=/bin/sh, do not
# hardcode /data/service/hnp/bin/bash; xeyes/xidle already-passed tests use
# the same pattern). No set -e/-u/pipefail: toybox ash rejects them; every
# assertion captures its own rc and always prints output so loader errors hit
# the log.
#
# 测试路径选择：myman -k 输出内置 MYMANKEYS（utils.c:155/218，"Keyboard
# Map"）后 exit(0)，-L 输出 MYMANLEGALNOTICE，-h 打印 usage——三条路径均在
# 显示后端初始化（XCurses Xinitscr / PDCurses initscr）之前退出，无需
# X server；Homebrew formula 的 test 同款 -k 路径。

MYMAN_BIN="$1"
LD_PRELOAD_EXTRA="${2:-}"

if [ -z "$MYMAN_BIN" ]; then
    echo "FAIL: myman binary path not provided"
    exit 1
fi

if [ ! -x "$MYMAN_BIN" ]; then
    echo "FAIL: $MYMAN_BIN not found or not executable"
    exit 1
fi

BIN_DIR=$(dirname "$MYMAN_BIN")
export LD_LIBRARY_PATH="${BIN_DIR}:${LD_LIBRARY_PATH:-}"

if [ -n "$LD_PRELOAD_EXTRA" ]; then
    export LD_PRELOAD="$LD_PRELOAD_EXTRA"
fi

echo "[shell] $0"
echo "[env] PATH=$PATH"
echo "[env] LD_LIBRARY_PATH=$LD_LIBRARY_PATH"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-}"

discovered=3
passed=0

# 诊断：musl ldd 打印每个 DT_NEEDED 的解析结果，缺库一目了然
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$MYMAN_BIN" 2>&1 || true
fi

echo "[test 1/$discovered] myman -k (keyboard map)"
k_output=$("$MYMAN_BIN" -k 2>&1)
rc=$?
echo "$k_output" | head -5
if [ $rc -ne 0 ]; then
    echo "FAIL: myman -k exit=$rc"
else
    # -k 打印内置 MYMANKEYS 字符串（utils.c:155，首行 "The following
    # case-insensitive keystroke commands..."）并在任何显示后端初始化
    # 之前 exit(0)。注意 MYMANKEYS_prefix（"Keyboard Map"）是独立常量，
    # -k 只输出 MYMANKEYS 主体，故断言首行文本。
    if echo "$k_output" | grep -q "keystroke commands"; then
        echo "PASS: myman -k reports keyboard map"
        passed=$((passed + 1))
    else
        echo "FAIL: unexpected myman -k output"
    fi
fi

echo "[test 2/$discovered] myman -L (legal notice)"
l_output=$("$MYMAN_BIN" -L 2>&1)
rc=$?
echo "$l_output" | head -3
if [ $rc -ne 0 ]; then
    echo "FAIL: myman -L exit=$rc"
else
    if [ -n "$l_output" ]; then
        echo "PASS: myman -L prints legal notice"
        passed=$((passed + 1))
    else
        echo "FAIL: myman -L output empty"
    fi
fi

echo "[test 3/$discovered] myman -h (usage)"
h_output=$("$MYMAN_BIN" -h 2>&1)
rc=$?
echo "$h_output" | head -3
if [ $rc -ne 0 ]; then
    echo "FAIL: myman -h exit=$rc"
else
    if echo "$h_output" | grep -q "Usage"; then
        echo "PASS: myman -h prints usage"
        passed=$((passed + 1))
    else
        echo "FAIL: unexpected myman -h output"
    fi
fi

if [ "$passed" -ne "$discovered" ]; then
    echo "FAIL: $((discovered - passed))/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_myman.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_myman.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
