#!/bin/sh
# test_package/test.sh — smoke test for bash executable
set -eu

echo "[test] bash --version"
bash --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    bash --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ bash failed both --version and --help"
        exit 1
    }
}
