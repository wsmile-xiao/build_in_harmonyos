#!/bin/bash
# test_package test_rogue.sh — bsdgames-nonfree 2.17 消费者测试
# rogue 为交互式 roguelike：stdin 输入名字 + quit 后正常退出，
# 启动横幅 "Hey!" 出现即证明二进制可执行且 curses 初始化正常。
set -euo pipefail

PASS=0
FAIL=0

check_rogue() {
    local bin="$1"
    if [ ! -x "$bin" ]; then
        echo "FAIL: rogue binary not found or not executable: $bin"
        FAIL=$((FAIL + 1))
        return
    fi
    local out status
    if out=$(printf "tester\nquit\ny\n" | "$bin" 2>&1); then
        status=0
    else
        status=$?
    fi
    if [ "$status" -eq 0 ] && printf '%s\n' "$out" | grep -q "Hey!"; then
        echo "PASS: rogue startup banner (exit $status, 'Hey!' found)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: rogue startup (exit $status, no 'Hey!' banner)"
        FAIL=$((FAIL + 1))
    fi
}

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path-to-rogue>"
    exit 2
fi

check_rogue "$1"

echo "bsdgames-nonfree consumer test: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ] && [ "$PASS" -ge 1 ]; then
    echo "ALL OK"
    exit 0
else
    echo "TEST FAILED"
    exit 1
fi
