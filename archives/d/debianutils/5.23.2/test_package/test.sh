#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for debianutils executables
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] run-parts --version"
run-parts --version && echo "✅ run-parts --version OK" || {
    echo "[test] run-parts --version failed, trying --help..."
    run-parts --help > /dev/null 2>&1 && echo "✅ run-parts --help OK" || {
        echo "❌ run-parts failed both --version and --help"
        exit 1
    }
}

echo "[test] ischroot --version"
ischroot --version && echo "✅ ischroot --version OK" || {
    echo "[test] ischroot --version failed, trying --help..."
    ischroot --help > /dev/null 2>&1 && echo "✅ ischroot --help OK" || {
        echo "❌ ischroot failed both --version and --help"
        exit 1
    }
}
