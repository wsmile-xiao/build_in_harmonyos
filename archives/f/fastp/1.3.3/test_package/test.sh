#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for fastp executable
set -eu

echo "[test] fastp --version"
fastp --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    fastp --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ fastp failed both --version and --help"
        exit 1
    }
}