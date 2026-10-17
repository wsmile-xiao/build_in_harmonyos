#!/bin/bash
# test_package/test.sh — smoke test for abi-compliance-checker
# (与 conanfile.py 的等效验证保持一致; 上游 RegTests 套件见 conanfile.py)
set -euo pipefail

echo "[test] abi-compliance-checker --version"
abi-compliance-checker --version 2>&1 | head -3

echo "[test] abi-compliance-checker --help"
abi-compliance-checker --help >/dev/null 2>&1 || {
    echo "❌ abi-compliance-checker --help failed"
    exit 1
}
echo "✅ abi-compliance-checker --help OK"

echo "[test] perl -c syntax check"
perl -c "$(command -v abi-compliance-checker)" >/dev/null 2>&1 || {
    echo "❌ perl -c failed"
    exit 1
}
echo "✅ perl -c syntax OK"
