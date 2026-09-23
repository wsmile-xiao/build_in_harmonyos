#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nvtop executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] nvtop --version"
if nvtop --version 2>&1; then
    echo "✅ nvtop --version OK"
else
    echo "[test] --version failed, trying --help..."
    if nvtop --help 2>&1; then
        echo "✅ nvtop --help OK"
    else
        echo "❌ nvtop failed both --version and --help"
        exit 1
    fi
fi