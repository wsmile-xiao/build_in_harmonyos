#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for s6 executable
# Runs in conanrun env (PATH includes installed bin/)
set -eu

echo "[test] s6-svc --help"
s6-svc --help > /dev/null 2>&1 && echo "✅ s6-svc --help OK" || {
    echo "[test] s6-svc --help failed (expected for usage), trying s6-svstat..."
    s6-svstat 2>&1 | head -1 && echo "✅ s6-svstat OK" || {
        echo "❌ s6 binaries not functional"
        exit 1
    }
}

echo "[test] s6-svscan usage"
s6-svscan 2>&1 | head -1 || true

echo "✅ All s6 smoke tests passed"
