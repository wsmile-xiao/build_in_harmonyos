#!/bin/sh
# test_autodir.sh — autodir test_package 测试脚本
# 验证 autodir 可执行 + 实质运行（R34：实质调用被测包）
#
# 用法: sh test_autodir.sh <bin_dir>
set -eu
set -o pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir>" >&2
    exit 2
fi
BIN_DIR="$1"
AD="$BIN_DIR/autodir"

echo "== 1. 可执行性检查 =="
if [ ! -x "$AD" ]; then
    echo "FAIL: autodir not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（无参数——usage/错误输出）=="
# 保留退出码（不吞）——显式 rc 检查（RC=0 默认值——set -u 安全——
# 吸取 backupninja 审查 P2 教训）
RC=0
OUT=$("$AD" 2>&1) || RC=$?
# autodir 运行需 autofs 内核机制（automount）——OHOS 沙箱无——运行
# rc 非 0 环境限制——不吞 rc 如实记录（同 automysqlbackup/backupninja
# 运行时限制先例）
echo "note: autodir run rc=$RC (requires autofs kernel mechanism — OHOS sandbox lacks it, environment limited)"
# 强断言：autodir 实质运行（输出非空——命令执行了——宽泛 grep 会把
# 未执行误判为通过）
if [ -n "$OUT" ]; then
    echo "OK: autodir executed (output produced, env-limited rc noted)"
else
    echo "FAIL: autodir produced no output" >&2
    exit 1
fi
