#!/usr/bin/env bash
# test_package/test.sh — smoke test for iodine executable
# Runs in conanrun env (PATH includes installed sbin/)
set -euo pipefail

echo "[step] iodine -v"
iodine -v && echo "        [ok] iodine -v" || {
    echo "        [fail] iodine -v failed"
    exit 1
}

echo "[step] iodined -v"
iodined -v && echo "        [ok] iodined -v" || {
    echo "        [fail] iodined -v failed"
    exit 1
}
