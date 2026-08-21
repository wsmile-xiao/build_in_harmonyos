#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for epstool executable
# Runs in conanrun env (PATH includes installed bin/)
# R34: Must actually invoke the epstool binary, not a stub.
set -eu

echo "[test] epstool --help"
epstool --help 2>&1 | head -3
if epstool --help 2>&1 | grep -q "epstool 3.09"; then
    echo "✅ epstool --help OK (version string found)"
else
    echo "❌ epstool --help did not show expected version"
    exit 1
fi
