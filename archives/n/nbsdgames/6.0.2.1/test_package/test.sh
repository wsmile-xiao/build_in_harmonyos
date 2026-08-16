#!/bin/bash
# test_package test.sh — nbsdgames 6.0.2.1 消费者测试
# 实测依据（2026-08-16 设备实测）：
#   上游 make test 为交互式冒烟入口（for game in ALL; do ./$game; done，逐个启动游戏等待键盘输入），
#   无 TTY 的 CI 环境无法完整自动化运行（14/23 游戏直接报 Error opening terminal）。
#   实测确认以下游戏支持 -h 并输出 Usage，可作非交互子集真实运行：
#     sudoku/reversi/checkers/sos —— 本脚本真实执行这 4 个游戏的 -h 冒烟验证。
set -euo pipefail

PASS=0
FAIL=0

check_game() {
    local game="$1" expect_exit="$2"
    local bin status out
    bin=$(command -v "$game" 2>/dev/null) || { echo "FAIL: $game binary not found"; FAIL=$((FAIL + 1)); return; }
    if out=$("$bin" -h 2>&1); then status=0; else status=$?; fi
    if [ "$status" -eq "$expect_exit" ] && printf '%s\n' "$out" | grep -q '^Usage:'; then
        echo "PASS: $game -h (exit $status, Usage output)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $game -h (exit $status, expected $expect_exit, no Usage output)"
        FAIL=$((FAIL + 1))
    fi
}

# sudoku: -h 输出 Usage，约定退出码 1（上游行为）
check_game sudoku 1
# reversi/checkers/sos: -h 输出 Usage，退出码 0（上游行为）
check_game reversi 0
check_game checkers 0
check_game sos 0

echo "nbsdgames consumer test: $PASS passed, $FAIL failed"
if [ "$FAIL" -eq 0 ] && [ "$PASS" -ge 4 ]; then
    echo "ALL OK"
    exit 0
else
    echo "TEST FAILED"
    exit 1
fi
