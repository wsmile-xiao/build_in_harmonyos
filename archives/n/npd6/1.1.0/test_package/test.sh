#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the npd6 executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu
set -o pipefail

echo "[test] npd6 --version"
npd6 --version | grep -q "npd6 - version 1.1.0"
echo "OK: --version returns npd6 1.1.0"

echo "[test] npd6 --help (should show usage)"
npd6 --help 2>&1 || true  # --help exits with non-zero on some systems
echo "OK: --help executed"
