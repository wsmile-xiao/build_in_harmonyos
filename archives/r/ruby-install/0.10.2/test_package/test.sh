#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ruby-install script
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[test] ruby-install --version"
ruby-install --version
echo "OK: --version executes successfully"

echo "[test] ruby-install --help"
ruby-install --help | head -5
echo "OK: --help produces output"
