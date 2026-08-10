#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for lha executable
set -eu

echo "[test] lha --version"
lha --version && echo "✅ --version OK" || {
    echo "❌ lha --version failed"
    exit 1
}

echo "[test] lha --help (archive operations)"
lha --help 2>&1 | head -5 || true

echo "✅ All smoke tests passed"
