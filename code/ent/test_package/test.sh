#!/bin/bash
# test_package test.sh — ent 0.14.6 消费者测试
set -euo pipefail

# 检查 entc 是否在 PATH 中
if command -v entc &>/dev/null; then
    entc --help 2>&1 | head -5
    echo "✅ entc is available and working"
    exit 0
else
    echo "⚠️ entc not found in PATH, checking common locations..."
    for dir in "$HOME/usr/local/bin" "/usr/local/bin" "/usr/bin"; do
        if [ -x "$dir/entc" ]; then
            "$dir/entc" --help 2>&1 | head -5
            echo "✅ entc found at $dir/entc"
            exit 0
        fi
    done
    echo "❌ entc binary not found"
    exit 1
fi