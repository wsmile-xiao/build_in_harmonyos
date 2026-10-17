#!/bin/bash
# test_megatools.sh — verify megatools binary and subcommand symlinks.
# Usage: test_megatools.sh <path-to-megatools-package-folder>

set -euo pipefail

PKG_DIR="$1"

if [ -z "$PKG_DIR" ]; then
    echo "ERROR: package folder not provided"
    exit 1
fi

# megatools 动态链接系统预编译库（libcurl/libffi/libpcre2，位于 ~/usr/local/lib），
# conanrun 环境不会自动注入该路径，运行时需显式设置
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$HOME/usr/local/lib"

BIN_DIR="$PKG_DIR/bin"

if [ ! -x "$BIN_DIR/megatools" ]; then
    echo "ERROR: $BIN_DIR/megatools not found or not executable"
    exit 1
fi

ASSERTION_COUNT=0
pass() {
    ASSERTION_COUNT=$((ASSERTION_COUNT + 1))
    echo "PASS: $1"
}
fail() {
    echo "FAIL: $1"
    exit 1
}

# Test 1: megatools --version outputs version string
# 上游 megatools 的 --version 不被识别为子命令，走 usage 分支打印版本后返回 1
# （tools/shell.c main() 末尾 return 1），因此不检查退出码，仅验证输出含版本标识
output=$("$BIN_DIR/megatools" --version 2>&1) || true
echo "$output" | grep -q "command line tools" || fail "megatools --version should print version info, got: $output"
pass "megatools --version outputs version info"

# Test 2: megatools --help outputs usage information（同上，退出码为 1 属上游行为）
output=$("$BIN_DIR/megatools" --help 2>&1) || true
echo "$output" | grep -qiE "usage|command|option" || fail "megatools --help should contain usage info, got: $output"
pass "megatools --help outputs usage info"

# Test 3: subcommand symlinks exist (megals, megadl)
for cmd in megals megadl; do
    if [ ! -x "$BIN_DIR/$cmd" ]; then
        fail "subcommand symlink $BIN_DIR/$cmd not found or not executable"
    fi
done
pass "subcommand symlinks (megals, megadl) exist"

echo ""
echo "All $ASSERTION_COUNT assertions passed."
