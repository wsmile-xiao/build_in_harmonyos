#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for osslsigncode executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] osslsigncode --version"
osslsigncode --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    osslsigncode --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ osslsigncode failed both --version and --help"
        exit 1
    }
}
