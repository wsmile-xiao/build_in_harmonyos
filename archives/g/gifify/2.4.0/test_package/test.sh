#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gifify executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] gifify --version"
gifify --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    gifify --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ gifify failed both --version and --help"
        exit 1
    }
}
