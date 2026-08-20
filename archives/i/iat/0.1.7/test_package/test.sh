#!/usr/bin/env bash
# test_package/test.sh — 验证 iat 二进制功能正常
set -euo pipefail

if iat --version 2>&1 | grep -q "0.1.7"; then
    echo "        [ok] iat --version outputs expected version"
else
    echo "        [fail] iat --version did not output expected version"
    exit 1
fi
