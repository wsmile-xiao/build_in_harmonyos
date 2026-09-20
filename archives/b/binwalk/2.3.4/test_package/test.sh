#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for binwalk (R34)
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] import binwalk module"
python3 -c "import binwalk; print(binwalk.__version__)" && echo "OK: import binwalk" || {
    echo "FAIL: import binwalk failed"
    exit 1
}

echo "[test] binwalk --help"
binwalk --help > /dev/null 2>&1 && echo "OK: --help works" || {
    echo "FAIL: binwalk --help failed"
    exit 1
}
