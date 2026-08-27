#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for akamai executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] akamai --version"
akamai --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    akamai --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ akamai failed both --version and --help"
        exit 1
    }
}
