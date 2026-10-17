#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for wg executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] wg --version"
wg --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    wg --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ wg failed both --version and --help"
        exit 1
    }
}
