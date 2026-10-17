#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for fish executable
set -euo pipefail

echo "[test] fish --version"
fish --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    fish --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ fish failed both --version and --help"
        exit 1
    }
}

echo "[test] fish -c 'echo hello'"
fish -c 'echo hello' | grep -q hello && echo "✅ fish -c OK" || {
    echo "❌ fish -c 'echo hello' failed"
    exit 1
}
