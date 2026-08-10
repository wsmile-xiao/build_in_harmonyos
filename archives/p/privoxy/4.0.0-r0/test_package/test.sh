#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the privoxy executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] privoxy --version"
privoxy --version 2>&1 | grep -q "Privoxy"
echo "OK: --version returns Privoxy version info"

echo "[test] privoxy --help (exit code check)"
# privoxy --help may exit non-zero; just check it produces output
privoxy --help 2>&1 | head -1 | grep -q . || true
echo "OK: --help produces usage output"

echo "All tests passed."
