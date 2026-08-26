#!/usr/bin/env bash
# test_package/test.sh — smoke test for isync (mbsync)
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] mbsync --version"
mbsync --version && echo "        [ok] mbsync --version passed" || {
        echo "        [fail] mbsync --version failed"
        exit 1
}
