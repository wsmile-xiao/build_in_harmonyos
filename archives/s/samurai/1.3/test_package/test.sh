#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for samu executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] samu --version"
samu --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    samu --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ samu failed both --version and --help"
        exit 1
    }
}
