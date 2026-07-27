#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for stress-ng executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] stress-ng --version"
stress-ng --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    stress-ng --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ stress-ng failed both --version and --help"
        exit 1
    }
}
