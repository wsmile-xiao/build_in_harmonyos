#!/bin/sh
# rampler 2.1.1 消费者测试（R34）——确定性行为断言
# 用法: test_rampler.sh <packaged-rampler-bin> [output-file]
set -e
BIN="$1"
OUT="${2:-rampler_out.txt}"
[ -x "$BIN" ] || { echo "FAIL: $BIN not executable"; exit 2; }

# ① 版本路径：`--version` 打印 "2.1.1"（已签名 ELF 可执行 + 依赖解析）
v=$("$BIN" --version 2>&1) || true
printf '%s\n' "$v" > "$OUT"
echo "$v" | grep -q "2\.1\.1" || { echo "FAIL: --version:"; cat "$OUT"; exit 1; }

# ② 给选项但缺位置参数 → main.cpp 的确定性错误路径（optind==argc）
e=$("$BIN" -o . 2>&1) || true
printf '%s\n' "$e" >> "$OUT"
echo "$e" | grep -q "missing arguments" || { echo "FAIL: missing-arguments:"; cat "$OUT"; exit 1; }

# ③ 无参数 → usage 分支（rc=0，验证 Help 路径可用）
h=$("$BIN" 2>&1) || true
printf '%s\n' "$h" >> "$OUT"
echo "$h" | grep -q "usage: rampler" || { echo "FAIL: usage:"; cat "$OUT"; exit 1; }

echo "rampler consumer test OK (version + missing-arguments + usage paths)"
