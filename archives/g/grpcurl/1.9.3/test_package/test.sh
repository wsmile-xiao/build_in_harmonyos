#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for grpcurl executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] grpcurl --version"
grpcurl --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    grpcurl --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ grpcurl failed both --version and --help"
        exit 1
    }
}
