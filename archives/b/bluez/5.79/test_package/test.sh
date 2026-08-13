#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bluez (R34: 实质执行被测包二进制)
set -eu

echo "[test] bluetoothctl --version"
bluetoothctl --version && echo "✅ bluetoothctl --version OK" || {
    echo "[test] --version failed, trying btmon..."
    btmon --version > /dev/null 2>&1 && echo "✅ btmon --version OK" || {
        echo "❌ bluez 工具均无法执行 --version"
        exit 1
    }
}
