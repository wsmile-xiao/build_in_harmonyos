#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for table-socketmap executable
# Argument 1: full path to the table-socketmap binary (passed by conanfile.py)
set -eu

BINARY="${1:?missing binary path}"

echo "[test] table-socketmap config|ready handshake"
output=$(echo "config|ready" | "$BINARY" /tmp/nonexistent.sock 2>&1 || true)

if echo "$output" | grep -q "register|ready"; then
    echo "✅ config|ready handshake OK"
else
    echo "❌ table-socketmap failed config|ready handshake"
    echo "output: $output"
    exit 1
fi
