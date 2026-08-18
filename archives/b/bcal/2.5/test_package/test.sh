#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bcal executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] bcal -h (version check)"
output=$(bcal -h 2>&1 || true)
if echo "$output" | grep -q "Version 2.5"; then
    echo "✅ bcal -h version OK"
else
    echo "❌ bcal -h failed to show version"
    exit 1
fi

echo "[test] bcal -c 255 (radix conversion)"
output=$(bcal -c 255 2>&1 || true)
if echo "$output" | grep -q "11111111"; then
    echo "✅ bcal -c 255 radix OK"
else
    echo "❌ bcal -c 255 radix conversion failed"
    exit 1
fi

echo "[test] bcal -m 1 kib (byte calculation)"
output=$(bcal -m 1 kib 2>&1 || true)
if echo "$output" | grep -q "1024"; then
    echo "✅ bcal -m 1 kib byte calc OK"
else
    echo "❌ bcal -m 1 kib byte calculation failed"
    exit 1
fi
