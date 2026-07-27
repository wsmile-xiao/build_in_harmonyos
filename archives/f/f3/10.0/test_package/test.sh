#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for f3 executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] f3write --version"
f3write --version && echo "✅ f3write --version OK" || {
    echo "[test] f3write --version failed, trying --help..."
    f3write --help > /dev/null 2>&1 && echo "✅ f3write --help OK" || {
        echo "❌ f3write failed both --version and --help"
        exit 1
    }
}

echo "[test] f3read --version"
f3read --version && echo "✅ f3read --version OK" || {
    echo "[test] f3read --version failed, trying --help..."
    f3read --help > /dev/null 2>&1 && echo "✅ f3read --help OK" || {
        echo "❌ f3read failed both --version and --help"
        exit 1
    }
}

echo "All tests passed."
