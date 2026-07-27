#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for wrk executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] wrk --version"
# wrk --version exits with code 1 (common for CLI tools), check output instead
output=$(wrk --version 2>&1 || true)
if echo "$output" | grep -q "wrk.*Copyright"; then
    echo "✅ --version OK"
    echo "$output" | head -1
else
    echo "❌ wrk --version did not produce expected output"
    echo "$output"
    exit 1
fi
