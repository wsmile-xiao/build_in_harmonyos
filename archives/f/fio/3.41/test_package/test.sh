#!/usr/bin/env bash
# test_package/test.sh — smoke test for fio executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] Running fio --version"
fio --version
echo "        [ok] fio --version passed"
