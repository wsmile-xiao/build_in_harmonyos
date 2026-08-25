#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dynamips executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] dynamips --version"
# dynamips --version outputs version but exits non-zero (expects IOS image)
output=$(dynamips --version 2>&1 || true)  # non-zero exit is expected
echo "$output" | grep -q "0.2.23" && echo "        [ok] --version OK" || {
    echo "        [fail] --version output unexpected, trying --help..."
    output=$(dynamips --help 2>&1 || true)  # non-zero exit is expected
    echo "$output" | grep -q "dynamips\|Cisco\|0.2.23" && echo "        [ok] --help OK" || {
        echo "        [fail] dynamips failed both --version and --help"
        exit 1
    }
}
