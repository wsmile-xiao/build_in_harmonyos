#!/bin/bash
# test_package test.sh — nbsdgames 6.0.2 消费者测试
set -euo pipefail

if command -v sudoku >/dev/null 2>&1; then
    if output=$(sudoku -h 2>&1); then
        status=0
    else
        status=$?
    fi
    test "$status" -eq 1
    printf '%s\n' "$output" | grep -q '^Usage:'
    echo "nbsdgames (sudoku) is available and working"
    exit 0
fi

echo "sudoku binary not found"
exit 1
