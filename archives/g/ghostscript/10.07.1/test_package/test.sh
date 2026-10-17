#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ghostscript executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] gs --version"
gs --version && echo "✅ gs --version OK" || {
    echo "[test] --version failed, trying --help..."
    gs --help > /dev/null 2>&1 && echo "✅ gs --help OK" || {
        echo "❌ gs failed both --version and --help"
        exit 1
    }
}
