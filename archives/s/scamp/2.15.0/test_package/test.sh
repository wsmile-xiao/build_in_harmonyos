#!/usr/bin/env bash
# test_package/test.sh — smoke test for scamp executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] scamp --version"
scamp --version && echo "✅ --version OK" || {
    echo "❌ scamp --version failed"
    exit 1
}
