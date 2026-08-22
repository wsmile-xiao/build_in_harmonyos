#!/data/service/hnp/bin/bash
# test_package/test_ncmpcpp.sh - smoke test for ncmpcpp executable
# Runs in the conanrun env (PATH includes the installed bin/)
set -euo pipefail

echo "[test] ncmpcpp --version"
ncmpcpp --version && echo "OK: --version ran" || {
    echo "FAIL: ncmpcpp --version"
    exit 1
}

echo "[test] version string contains 0.10.1"
ncmpcpp --version | grep -q "0.10.1" || {
    echo "FAIL: version output does not contain 0.10.1"
    exit 1
}

echo ""
echo "All ncmpcpp smoke tests passed."
