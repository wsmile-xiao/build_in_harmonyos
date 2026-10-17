#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the comptext executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -euo pipefail

echo "[test] comptext --version"
OUT=$(comptext --version 2>&1) || { echo "FAIL: --version rc=$?"; exit 1; }
echo "  output: $OUT"
echo "$OUT" | grep -q "Version:" || { echo "FAIL: --version 未输出 Version 信息"; exit 1; }
echo "OK: --version returns version info"

echo "[test] comptext --help"
OUT=$(comptext --help 2>&1) || { echo "FAIL: --help rc=$?"; exit 1; }
echo "$OUT" | grep -q -- "--version" || { echo "FAIL: --help 未列出 --version 选项"; exit 1; }
echo "OK: --help lists --version option"

echo "comptext test_package PASS"
