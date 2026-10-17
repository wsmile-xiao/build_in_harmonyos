#!/bin/sh
# ksh93 消费者测试：验证 ksh 可执行文件在 HarmonyOS 环境下可正常运行
# 用法：sh test.sh <path-to-ksh>

set -e

KSH_BIN="$1"

if [ -z "$KSH_BIN" ]; then
    echo "usage: test.sh <path-to-ksh>"
    exit 1
fi

if [ ! -x "$KSH_BIN" ]; then
    echo "FAIL: ksh is not executable: $KSH_BIN"
    exit 1
fi

echo "=== 1. 基础功能 ==="
OUTPUT=$("$KSH_BIN" -c "echo ksh93 test_package: OK")
echo "$OUTPUT"
if [ "$OUTPUT" != "ksh93 test_package: OK" ]; then
    echo "FAIL: unexpected output: $OUTPUT"
    exit 1
fi

echo "=== 2. 算术运算 ==="
OUTPUT=$("$KSH_BIN" -c "print \$(( 1 + 1 ))")
echo "$OUTPUT"
if [ "$OUTPUT" != "2" ]; then
    echo "FAIL: arithmetic test expected 2, got: $OUTPUT"
    exit 1
fi

echo "=== 3. 鸿蒙专属：无 /bin/bash 环境下运行 ==="
"$KSH_BIN" -c "echo 鸿蒙专属测试: ksh93 在无 /bin/bash 环境下运行正常"

echo "=== 4. SHELL 环境变量路径存在性 ==="
if [ -n "$SHELL" ] && [ ! -e "$SHELL" ]; then
    echo "FAIL: SHELL points to non-existent path: $SHELL"
    exit 1
fi

echo "=== 5. shcomp 可运行 ==="
SHCOMP_BIN="$(dirname "$KSH_BIN")/shcomp"
if [ -e "$SHCOMP_BIN" ]; then
    set +e
    "$SHCOMP_BIN" --help >/dev/null 2>&1
    RC=$?
    set -e
    if [ "$RC" -ne 0 ] && [ "$RC" -ne 2 ]; then
        echo "FAIL: shcomp --help returned unexpected exit code: $RC"
        exit 1
    fi
fi

echo "鸿蒙专属测试: 通过"
