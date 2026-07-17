#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for yadm executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] yadm --version"
yadm --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    yadm --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ yadm failed both --version and --help"
        exit 1
    }
}
