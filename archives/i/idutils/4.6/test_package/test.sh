#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for idutils executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] mkid --version"
mkid --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    mkid --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ mkid failed both --version and --help"
        exit 1
    }
}

echo "[test] lid --version"
lid --version || {
    echo "[test] lid --version failed, trying --help..."
    lid --help > /dev/null 2>&1 || {
        echo "❌ lid failed both --version and --help"
        exit 1
    }
}
