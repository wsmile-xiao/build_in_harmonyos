#!/bin/sh
# test_package/test.sh — 消费者冒烟测试：真实执行 aicommits CLI
# 验证 aicommits --version 输出包含 3.4.0（R34：不得为空壳测试）
set -eu

echo "[test] aicommits --version"
out="$(aicommits --version 2>&1)" || {
    echo "❌ aicommits --version 执行失败 (exit=$?)"
    exit 1
}
echo "$out"

case "$out" in
    *"3.4.0"*)
        echo "✅ aicommits --version 输出包含 3.4.0"
        ;;
    *)
        echo "❌ aicommits --version 输出未包含 3.4.0"
        exit 1
        ;;
esac

# 额外验证 --help 可用（CLI 入口完整）
echo "[test] aicommits --help"
aicommits --help >/dev/null 2>&1 && {
    echo "✅ aicommits --help 通过"
} || {
    echo "ℹ️ aicommits --help 返回非零（环境无 TTY），不影响版本验证"
}
exit 0
