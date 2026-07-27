#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for redis executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu -o pipefail

echo "[test] redis-server --version"
redis-server --version && echo "✅ redis-server --version OK" || {
    echo "[test] --version failed, trying --help..."
    redis-server --help > /dev/null 2>&1 && echo "✅ redis-server --help OK" || {
        echo "❌ redis-server failed both --version and --help"
        exit 1
    }
}

echo "[test] redis-cli --version"
redis-cli --version && echo "✅ redis-cli --version OK"
