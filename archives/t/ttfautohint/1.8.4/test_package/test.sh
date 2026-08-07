#!/usr/bin/env bash
# test_package/test.sh — ttfautohint 1.8.4 CLI smoke test
#
# 真调 ttfautohint 二进制, grep 验证 --version / --help 输出.
# 失败 (grep 不匹配 / 二进制崩溃) → exit 1, 阻止 conan create 产出.
set -euo pipefail

# Test 1: --version 必须输出版本号 1.8.4
if ttfautohint --version 2>&1 | grep -q "1.8.4"; then
    echo "[ok] ttfautohint --version outputs 1.8.4"
else
    echo "[fail] ttfautohint --version did not output expected version"
    exit 1
fi

# Test 2: --help 必须输出用法说明 (含 ttfautohint 自身名)
if ttfautohint --help 2>&1 | grep -q "ttfautohint"; then
    echo "[ok] ttfautohint --help outputs usage"
else
    echo "[fail] ttfautohint --help did not output expected usage"
    exit 1
fi

echo "[ok] all ttfautohint smoke tests passed"
