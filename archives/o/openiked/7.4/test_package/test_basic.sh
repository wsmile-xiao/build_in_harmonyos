#!/bin/sh
# openiked 7.4 消费者测试（R34）
# 用法: test_basic.sh <package-bin-dir>
# 断言1: iked -V 输出 "OpenIKED" 且 rc=0（ELF 可执行 + 链接正确）
# 断言2: ikectl 无参调用 rc!=0 且有输出（命令列表/usage，控制面可执行）
set -e
BIN="$1"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# 1) iked -V
"$BIN/iked" -V > "$OUT/v.txt" 2>&1
rc=$?
echo "iked -V rc=$rc out=$(cat $OUT/v.txt)"
[ "$rc" -eq 0 ] || { echo "FAIL: iked -V rc=$rc"; exit 1; }
grep -q "OpenIKED" "$OUT/v.txt" || { echo "FAIL: no OpenIKED banner"; cat "$OUT/v.txt"; exit 1; }

# 2) ikectl usage
"$BIN/ikectl" > "$OUT/ctl.txt" 2>&1 || rc2=$?
rc2=${rc2:-0}
echo "ikectl no-arg rc=$rc2"
[ "$rc2" -ne 0 ] || { echo "FAIL: ikectl no-arg should fail"; exit 1; }
[ -s "$OUT/ctl.txt" ] || { echo "FAIL: ikectl produced no output"; exit 1; }

echo "openiked basic assertions OK"
