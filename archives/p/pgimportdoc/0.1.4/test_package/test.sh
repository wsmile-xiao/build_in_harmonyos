#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for pgimportdoc executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] pgimportdoc --version"
pgimportdoc --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    pgimportdoc --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ pgimportdoc failed both --version and --help"
        exit 1
    }
}
