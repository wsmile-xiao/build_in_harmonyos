#!/bin/sh
# test_autorevision.sh — autorevision test_package 测试脚本
# 验证 autorevision 可执行 + 实际运行（R34：实质调用被测包）
#
# 用法: sh test_autorevision.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
ARV="$BIN_DIR/autorevision"

echo "== 1. 可执行性检查 =="
if [ ! -x "$ARV" ]; then
    echo "FAIL: autorevision not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（-s VCS_TYPE 查询）=="
# 保留退出码（不吞）——显式 rc 检查
RC=0
OUT=$("$ARV" -s VCS_TYPE 2>&1) || RC=$?
if [ "$RC" -ne 0 ]; then
    echo "FAIL: autorevision failed (rc=$RC): $OUT" >&2
    exit 1
fi
# 强断言：VCS_TYPE 查询输出有效类型（git/svn/hg/...——宽泛 grep 会把
# 崩溃输出误判为通过）
if echo "$OUT" | grep -qE "^(git|svn|hg|bzr|fossil|unknown|cvs|darcs)$"; then
    echo "OK: autorevision ran successfully (VCS_TYPE=$OUT)"
else
    echo "FAIL: autorevision did not produce expected output: $OUT" >&2
    exit 1
fi
