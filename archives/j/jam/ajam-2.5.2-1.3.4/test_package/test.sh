#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for jam executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] jam -v"
jam -v && echo "✅ jam -v OK" || {
    echo "❌ jam -v failed"
    exit 1
}
