#!/bin/sh
# prep-test.sh - 测试前置准备（鸿蒙特有）
# 用法：./scripts/prep-test.sh [安装目录]
# 封装 KNOW_YOUR_WHY.md D5 的三个强制步骤

set -e

INSTALL_DIR="${1:-$DEFAULT_PREFIX}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== 鸿蒙测试前置准备 ==="

# Step 1: 预确认弹窗
echo ""
echo "1/3 预确认弹窗（触发所有新编译的二进制首次运行确认）..."
if [ -d "$INSTALL_DIR/bin" ]; then
    count=0
    for bin in "$INSTALL_DIR/bin"/*; do
        [ -f "$bin" ] || continue
        "$bin" --version >/dev/null 2>&1 || true
        count=$((count + 1))
    done
    echo "   $GREEN✅ 已触发 $count 个二进制的首次运行确认$NC"
else
    echo "   $YELLOW⚠️ $INSTALL_DIR/bin 不存在，跳过$NC"
fi

# Step 2: 禁止并行测试
echo ""
echo "2/3 禁止并行测试（鸿蒙 FIFO 限制）..."
export MAKEFLAGS="-j1"
echo "   $GREEN✅ MAKEFLAGS=-j1$NC"

# Step 3: 设置超时
echo ""
echo "3/3 提醒设置超时..."
echo "   $YELLOW⚠️ 建议使用: timeout 1800 make check$NC"
echo "   $YELLOW⚠️ 防止测试卡住导致会话超时$NC"

echo ""
echo "=== 准备完成，可以开始测试 ==="
echo "推荐命令: timeout 1800 make check"
