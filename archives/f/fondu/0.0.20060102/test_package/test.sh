#!/usr/bin/env zsh
# test_package/test.sh — 验证 fondu 二进制功能正常
# fondu 无参数/未知选项时打印 Usage 到 stderr 并退出码 0（见 fondu.c main()）
# 用法: test.sh <fondu 二进制路径>
set -euo pipefail

FONDU_BIN="${1:-fondu}"

if "$FONDU_BIN" -h 2>&1 | grep -q "Usage"; then
    echo "        [ok] fondu -h prints usage"
else
    echo "        [fail] fondu -h did not print usage"
    exit 1
fi
