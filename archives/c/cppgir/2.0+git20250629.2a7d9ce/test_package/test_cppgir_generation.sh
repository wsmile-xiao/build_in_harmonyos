#!/usr/bin/env bash
# test_cppgir_generation.sh — cppgir test_package 驱动脚本
# 用最小 Test-1.0.gir 驱动安装的 cppgir 生成器，断言生成的 C++ 绑定包含预期内容。
# 用法: test_cppgir_generation.sh <cppgir_bin> <gir_dir> <out_dir>
set -euo pipefail

CPPGIR_BIN="$1"
GIR_DIR="$2"
OUT_DIR="$3"

mkdir -p "$OUT_DIR"
"$CPPGIR_BIN" --output "$OUT_DIR" --gir-path "$GIR_DIR" Test-1.0

# 断言生成产物完整
test -f "$OUT_DIR/test/test.hpp" || { echo "FAIL: missing test/test.hpp"; exit 1; }
test -f "$OUT_DIR/test/_functions.hpp" || { echo "FAIL: missing test/_functions.hpp"; exit 1; }

# 断言绑定内容：函数 test_add 的 C++ 声明存在
grep -q "test_add" "$OUT_DIR/test/_functions.hpp" || { echo "FAIL: test_add binding missing"; exit 1; }
grep -q "gint" "$OUT_DIR/test/_functions.hpp" || { echo "FAIL: gint types missing"; exit 1; }

echo "PASS: cppgir GIR->C++ generation verified (test_add binding present)"
