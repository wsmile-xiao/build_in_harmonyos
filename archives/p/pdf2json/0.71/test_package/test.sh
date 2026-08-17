#!/usr/bin/env zsh
# test_package/test.sh — 验证 pdf2json 二进制功能正常
set -euo pipefail

if pdf2json -v 2>&1 | grep -q "pdf2json"; then
    echo "        [ok] pdf2json -v outputs expected version string"
else
    echo "        [fail] pdf2json -v did not output expected version string"
    exit 1
fi
