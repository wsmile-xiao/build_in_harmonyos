#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the gnudos executables (mino, prime)
# Runs in conanrun env (resolves the packaged ncurses dependency at runtime).
# R34: genuinely exercises the tested package's binaries.
set -euo pipefail

echo "[test] mino --version"
mino --version 2>&1 | grep -q "2.1"
echo "OK: mino --version reports 2.1"

echo "[test] prime --version"
prime --version 2>&1 | grep -q "2.1"
echo "OK: prime --version reports 2.1"

echo "ALL CONSUMER TESTS PASSED"
