#!/bin/sh
# test_package/test.sh — 消费者冒烟测试：验证 mod_radius.so 模块可用性
set -eu

MOD="${1:-}"

echo "[test] mod_radius.so 存在性"
[ -n "$MOD" ] && [ -f "$MOD" ] || {
    echo "❌ mod_radius.so 不存在: $MOD"
    exit 1
}
echo "✅ mod_radius.so 存在: $MOD"

echo "[test] ELF 魔数校验"
magic="$(dd if="$MOD" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' ')"
case "$magic" in
    *7f454c46*)
        echo "✅ mod_radius.so 为合法 ELF"
        ;;
    *)
        echo "❌ mod_radius.so 不是合法 ELF (magic=$magic)"
        exit 1
        ;;
esac

echo "[test] radius_module 符号校验"
if strings "$MOD" 2>/dev/null | grep -q "radius_module"; then
    echo "✅ mod_radius.so 含 radius_module 符号"
else
    echo "❌ mod_radius.so 缺少 radius_module 符号"
    exit 1
fi
exit 0
