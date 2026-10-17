#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for fig2dev executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] fig2dev --version"
fig2dev --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    fig2dev --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ fig2dev failed both --version and --help"
        exit 1
    }
}
