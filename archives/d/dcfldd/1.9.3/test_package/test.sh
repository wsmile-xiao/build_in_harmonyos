#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dcfldd executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] dcfldd --version"
dcfldd --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    dcfldd --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ dcfldd failed both --version and --help"
        exit 1
    }
}
