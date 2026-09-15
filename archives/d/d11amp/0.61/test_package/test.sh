#!/bin/bash
# test_package for d11amp 0.61 — 实质验证 (R34)
# 1) d11amp --version 断言输出版本 0.61
# 2) d11amp --help 断言帮助输出可读
set -euo pipefail

fail() { echo "test FAILED: $1"; exit 1; }

# locate installed binary
D11AMP_BIN="$(command -v d11amp || which d11amp || echo d11amp)"

echo "=== d11amp --version ==="
VERSION_OUT="$("$D11AMP_BIN" --version 2>&1)"
echo "output: [$VERSION_OUT]"
[ "$VERSION_OUT" = "0.61" ] || fail "--version 期望 '0.61' 实际 '$VERSION_OUT'"

echo "=== d11amp --help ==="
# --help 走 GTK 参数解析，无显示环境可能非零退出；仅断言帮助文本可读，
# 因此允许退出码非 0（内容才是断言对象）。
HELP_OUT="$("$D11AMP_BIN" --help 2>&1 || true)"
echo "$HELP_OUT" | grep -q "d11amp" || fail "--help 输出缺少 d11amp"

echo "test OK"
exit 0