#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for osv-scanner and osv-reporter binaries
set -eu

BIN_DIR="${1:-.}"

echo "[test] osv-scanner --version"
"${BIN_DIR}/osv-scanner" --version && echo "✅ osv-scanner --version OK" || {
    echo "❌ osv-scanner --version failed"
    exit 1
}

echo "[test] osv-reporter --version"
"${BIN_DIR}/osv-reporter" --version && echo "✅ osv-reporter --version OK" || {
    echo "❌ osv-reporter --version failed"
    exit 1
}
