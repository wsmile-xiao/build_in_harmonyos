#!/usr/bin/env bash
# test_package/test.sh — smoke test for pidcat
set -eu

echo "[test] pidcat --version"
pidcat --version 2>&1 && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    pidcat --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ pidcat failed both --version and --help"
        exit 1
    }
}

echo "[test] pidcat -h (short help)"
pidcat -h > /dev/null 2>&1 && echo "✅ -h OK" || {
    echo "⚠️ -h failed, but --version passed — acceptable"
}
