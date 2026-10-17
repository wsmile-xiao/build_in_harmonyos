#!/bin/sh
# test_package/test.sh — augustus-game 冒烟测试
# 用法: test.sh <augustus 二进制绝对路径>（由 test_package/conanfile.py 调用）
set -eu

BIN="$1"
echo "[test] $BIN --version"
OUT="$("$BIN" --version)"
echo "$OUT"

# 断言 1: 退出码为 0（set -e 已保证）
# 断言 2: 输出含程序名与版本
case "$OUT" in
  *augustus*4.0.0*)
    echo "[test] ✅ --version OK"
    ;;
  *)
    echo "[test] ❌ unexpected version output"
    exit 1
    ;;
esac
