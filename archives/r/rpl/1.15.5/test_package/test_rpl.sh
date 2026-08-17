#!/bin/sh
# test_rpl.sh — rpl test_package 测试脚本
# 验证 rpl 可执行 + 实际文本替换（R34：实质调用被测包）
#
# 用法: sh test_rpl.sh <bin_dir> [<tmp_dir>] [<python3_path>]
# 用显式 python3 调用 rpl wrapper（CI 的 conanrun 不含 python PATH，
# wrapper shebang `env python3` 找不到解释器）
set -e

if [ $# -lt 2 ]; then
    echo "usage: $0 <bin_dir> <tmp_dir> [<python3_path>]" >&2
    exit 2
fi
if [ -z "$2" ]; then
    echo "FAIL: tmp_dir must not be empty" >&2
    exit 2
fi
BIN_DIR="$1"
RPL="$BIN_DIR/rpl"
PY="${3:-python3}"

echo "== 1. 可执行性检查 =="
if [ ! -x "$RPL" ]; then
    echo "FAIL: rpl not executable" >&2
    exit 1
fi

echo "== 2. 实际文本替换 =="
TMP_DIR="$2/rpl-test"
mkdir -p "$TMP_DIR"
printf 'hello world\nfoo bar\n' > "$TMP_DIR/sample.txt"

# rpl 内部用 tempfile 创建临时文件再 rename 替换目标文件；CI 的系统
# TMPDIR（/data/storage/el2/base/cache）权限可能导致临时文件创建/rename
# 静默失败 → 显式设置 TMPDIR 指向可写目录（$2，test_package mkdtemp 创建）
export TMPDIR="$2"

# set +e 包裹命令替换：rpl 替换成功/失败都可能返回非 0，先捕获 RC
# 再恢复 errexit，使错误处理分支真正可达（AI 检视 P2 修复）
set +e
OUT=$("$PY" "$RPL" "hello" "goodbye" "$TMP_DIR/sample.txt" 2>&1)
RC=$?
set -e
if [ "$RC" -ne 0 ] && [ "$RC" -ne 1 ]; then
    echo "FAIL: rpl failed (rc=$RC): $OUT" >&2
    exit 1
fi
if grep -q "goodbye world" "$TMP_DIR/sample.txt"; then
    echo "OK: rpl replaced hello → goodbye"
else
    echo "FAIL: rpl did not replace text: $(cat "$TMP_DIR/sample.txt")" >&2
    echo "FAIL: rpl output was: $OUT" >&2
    exit 1
fi
rm -rf "$TMP_DIR"
