#!/bin/sh
# Consumer CLI test for libuninum 2.7 — end-to-end numconv conversion.
#
# 用法: sh test_cli.sh <numconv 绝对路径>
#
# 验证知识草稿 DRAFT-libuninum-2.7-lp64-ilp32-type-assumption-defects 中
# 两个 LP64 补丁的端到端可用性：
# - 0002（UTF8in 零长度 read 过量吞读）：修复前多字符输入只读到首字符；
# - 0003（putu8s/fputu8 wchar_t 与 UTF32* 混用）：修复前输出只出首字符。
# 断言 "6453" 经 Western -> Arabic_Western 转换输出完整的 4 个阿拉伯-印度
# 数字字符（8 字节 UTF-8：٦٤٥٣），而非修复前的单字符。
set -e

NUMCONV="$1"
if [ -z "$NUMCONV" ] || [ ! -x "$NUMCONV" ]; then
  echo "test_cli.sh: numconv not provided or not executable: $NUMCONV" >&2
  exit 1
fi

actual=$(printf '6453\n' | "$NUMCONV" -f Western -t Arabic_Western)
# ٦(331\246) ٤(331\244) ٥(331\245) ٣(331\243) — 4 字符 8 字节
expected=$(printf '\331\246\331\244\331\245\331\243')

actual_bytes=$(printf '%s' "$actual" | wc -c | tr -d ' ')
expected_bytes=$(printf '%s' "$expected" | wc -c | tr -d ' ')

if [ "$actual_bytes" != "$expected_bytes" ]; then
  echo "test_cli.sh: output truncated (got $actual_bytes bytes, want $expected_bytes)" >&2
  exit 1
fi
if [ "$actual" != "$expected" ]; then
  echo "test_cli.sh: output mismatch" >&2
  exit 1
fi

# 反向转换：٦٤٥٣ -> Devanagari 应得到 ६४५३（Western 为 cover 系统只进不出，
# 不能作 -t 输出目标；Devanagari 为 NS_TYPE_SAFE 双向系统）
reverse=$(printf '\331\246\331\244\331\245\331\243\n' | "$NUMCONV" -f Arabic_Western -t Devanagari)
# ६(340\245\254) ४(340\245\252) ५(340\245\253) ३(340\245\251)
expected_reverse=$(printf '\340\245\254\340\245\252\340\245\253\340\245\251')
if [ "$reverse" != "$expected_reverse" ]; then
  echo "test_cli.sh: reverse conversion mismatch (got $reverse)" >&2
  exit 1
fi

echo "test_cli.sh: numconv end-to-end conversion OK"
