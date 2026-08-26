#!/data/service/hnp/bin/bash
# test_package/test_vmdktool.sh — smoke test for the vmdktool executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] vmdktool --version"
vmdktool --version | grep -q "vmdktool"
echo "OK: --version returns vmdktool version string"

echo "[test] vmdktool --help"
vmdktool --help
echo "OK: --help exits successfully"
