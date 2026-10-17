#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for alpine-make-vm-image executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] alpine-make-vm-image --version"
alpine-make-vm-image --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    alpine-make-vm-image --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ alpine-make-vm-image failed both --version and --help"
        exit 1
    }
}
