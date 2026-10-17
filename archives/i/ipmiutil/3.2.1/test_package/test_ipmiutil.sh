#!/bin/sh
# test_ipmiutil.sh — ipmiutil test_package 测试脚本
# 验证 ipmiutil 可执行 + 实际版本/帮助信息输出（R34：实质调用被测包）
#
# 用法: sh test_ipmiutil.sh <bin_dir> [<tmp_dir>]
set -e

if [ $# -lt 1 ]; then
    echo "usage: $0 <bin_dir> [<tmp_dir>]" >&2
    exit 2
fi
BIN_DIR="$1"
IPMIUTIL="$BIN_DIR/ipmiutil"

echo "== 1. 可执行性检查 =="
if [ ! -x "$IPMIUTIL" ]; then
    echo "FAIL: ipmiutil not executable" >&2
    exit 1
fi

echo "== 2. 实际运行（帮助/版本信息）=="
# ipmiutil 无 IPMI 设备时以错误码退出，但会输出用法/版本信息 →
# 分别尝试 --help/-h/-v，任一成功即验证可执行；输出须含 ipmiutil 标识
OUT=$("$IPMIUTIL" --help 2>&1 || "$IPMIUTIL" -h 2>&1 || true)
if echo "$OUT" | grep -qi "ipmiutil"; then
    echo "OK: ipmiutil ran successfully (help output detected)"
else
    echo "FAIL: ipmiutil did not produce expected output: $OUT" >&2
    exit 1
fi
