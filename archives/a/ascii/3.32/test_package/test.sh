#!/usr/bin/env zsh
# test_package/test.sh — 验证 ascii 二进制功能正常
set -euo pipefail

if ascii -v 2>&1 | grep -q "3.32"; then
    echo "        [ok] ascii -v outputs expected version"
else
    echo "        [fail] ascii -v did not output expected version"
    exit 1
fi
