#!/bin/sh
# test_inxi.sh — inxi test_package 测试脚本
# 验证 inxi 可执行 + 实际版本信息输出（R34：实质调用被测包）
#
# 用法: sh test_inxi.sh <bin_dir>
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
INXI="$BIN_DIR/inxi"

echo "== 1. 可执行性检查 =="
if [ ! -x "$INXI" ]; then
    echo "FAIL: inxi not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（版本信息）=="
# 分别尝试 --version 与 -V，捕获输出；成功后用版本号匹配验证
if OUT=$("$INXI" --version 2>/dev/null) || OUT=$("$INXI" -V 2>/dev/null); then
    if echo "$OUT" | grep -qE "[0-9]+\.[0-9]+"; then
        echo "OK: inxi ran successfully (version output detected)"
    else
        echo "FAIL: inxi did not produce expected output: $OUT" >&2
        exit 1
    fi
else
    echo "FAIL: inxi failed to run" >&2
    exit 1
fi
