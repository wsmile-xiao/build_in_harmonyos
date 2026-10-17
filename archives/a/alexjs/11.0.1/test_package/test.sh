#!/bin/sh
# test_package/test.sh — 消费者冒烟测试：真实执行打包后的 alex CLI
# 验证 alex --version 输出包含 11.0.1，且 --stdin 敏感词检测生效
# （R34：非空壳测试 — 实际调用被测包 bin/alex）
set -eu

BIN="${1:-alex}"

echo "[test] $BIN --version"
out="$("$BIN" --version 2>&1)" || {
    echo "❌ $BIN --version 执行失败 (exit=$?)"
    exit 1
}
echo "$out"

case "$out" in
    *"11.0.1"*)
        echo "✅ $BIN --version 输出包含 11.0.1"
        ;;
    *)
        echo "❌ $BIN --version 输出未包含 11.0.1"
        exit 1
        ;;
esac

echo "[test] $BIN --stdin（敏感词检测，期望 exit 1 + 警告）"
sample="The boogeyman is a he.
"
set +e
warn_out="$(printf '%s' "$sample" | "$BIN" --stdin 2>&1)"
rc=$?
set -e
echo "$warn_out"
if [ "$rc" -ne 1 ]; then
    echo "❌ 敏感词输入应返回 exit 1（实际 rc=$rc）"
    exit 1
fi
case "$warn_out" in
    *"boogeyman"*|*"he"*)
        echo "✅ 敏感词警告已输出"
        ;;
    *)
        echo "❌ 未检测到敏感词警告"
        exit 1
        ;;
esac

echo "[test] $BIN --stdin（干净文本，期望 exit 0 无警告）"
clean="The quick brown fox jumps over the lazy dog.
"
set +e
clean_out="$(printf '%s' "$clean" | "$BIN" --stdin 2>&1)"
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
    echo "❌ 干净文本应返回 exit 0（实际 rc=$rc）"
    exit 1
fi
echo "✅ 干净文本通过（无警告）"

echo "alexjs test_package: 3/3 checks passed"
exit 0
