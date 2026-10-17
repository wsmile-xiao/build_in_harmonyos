#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dhcpstarv executable
# r60: 显式接收二进制路径（conanrun PATH 在 OHOS 下不保证含包 bin）
# 用法: test.sh <dhcpstarv 二进制路径>
set -eu

BIN="${1:-dhcpstarv}"

echo "[test] $BIN --version"
"$BIN" --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    "$BIN" --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ $BIN failed both --version and --help"
        exit 1
    }
}
