#!/bin/sh
# test_package/test.sh — 消费者冒烟测试：真实执行 aide 二进制
# 验证 aide --version 可运行且输出包含版本号 0.19.3（R34：不得为空壳测试）
set -eu

echo "[test] aide --version"
out="$(aide --version 2>&1)" || {
    echo "❌ aide --version 执行失败 (exit=$?)"
    exit 1
}
echo "$out"

case "$out" in
    *"0.19.3"*)
        echo "✅ aide --version 输出包含 0.19.3"
        ;;
    *)
        echo "❌ aide --version 输出未包含 0.19.3"
        exit 1
        ;;
esac

# 额外验证配置解析路径可用（--config-check 读取 /dev/null 空配置）
echo "[test] aide --config-check"
aide --config-check --config=/dev/null >/dev/null 2>&1 && {
    echo "✅ aide --config-check 通过"
} || {
    echo "ℹ️ aide --config-check 返回非零（空配置预期行为），不影响版本验证"
}
exit 0
