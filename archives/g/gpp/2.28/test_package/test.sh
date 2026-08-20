#!/usr/bin/env bash
# test_package/test.sh — 验证 gpp 二进制功能正常
set -euo pipefail

# Verify --version output contains expected version string
if gpp --version 2>&1 | grep -q "2.28"; then
    echo "        [ok] gpp --version outputs expected version"
else
    echo "        [fail] gpp --version did not output expected version"
    exit 1
fi

# Verify preprocessing: define a macro then reference it on the next line
# gpp processes #define FOO bar (defines macro), then FOO (expands to bar)
result=$(printf '#define FOO bar\nFOO\n' | gpp 2>&1)
if echo "$result" | grep -q "bar"; then
    echo "        [ok] gpp macro expansion works"
else
    echo "        [fail] gpp macro expansion failed"
    exit 1
fi
