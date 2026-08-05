#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for abi-compliance-checker
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] abi-compliance-checker --version"
abi-compliance-checker --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying -dumpversion..."
    abi-compliance-checker -dumpversion && echo "✅ -dumpversion OK" || {
        echo "❌ abi-compliance-checker failed both --version and -dumpversion"
        exit 1
    }
}
