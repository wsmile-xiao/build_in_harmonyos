#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for darkhttpd executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] darkhttpd --version"
# darkhttpd --version prints version then starts listening (does not exit)
# Use timeout to kill it, but capture output first to avoid pipefail issues
output=$(timeout 3 darkhttpd --version 2>&1 || true)
echo "$output" | head -1 | grep -q "darkhttpd/1.17" && echo "✅ --version OK" || {
    echo "❌ darkhttpd --version failed"
    exit 1
}
