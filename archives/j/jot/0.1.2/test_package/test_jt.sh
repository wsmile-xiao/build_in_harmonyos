#!/bin/sh
# test_jt.sh — jot test_package 测试脚本
# 验证 jt 可执行 + 实际运行（R34：实质执行被测包二进制）
#
# 用法: sh test_jt.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
JT="$BIN_DIR/jt"

echo "== 1. 可执行性检查 =="
if [ ! -x "$JT" ]; then
    echo "FAIL: jt not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（jt --help 应输出用法并成功退出）=="
# 保留退出码（不吞）——崩溃/失败即 FAIL
if ! OUT=$("$JT" --help 2>&1); then
    echo "FAIL: jt failed (rc=$?): $OUT" >&2
    exit 1
fi
# 强断言：帮助/用法输出非空（宽泛地确认二进制真实运行并产出内容）
if [ -n "$OUT" ]; then
    echo "OK: jt ran successfully (non-empty output)"
else
    echo "FAIL: jt produced empty output: $OUT" >&2
    exit 1
fi
