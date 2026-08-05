#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for api-sanity-checker
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] api-sanity-checker --version"
api-sanity-checker --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying -dumpversion..."
    api-sanity-checker -dumpversion && echo "✅ -dumpversion OK" || {
        echo "❌ api-sanity-checker failed both --version and -dumpversion"
        exit 1
    }
}
