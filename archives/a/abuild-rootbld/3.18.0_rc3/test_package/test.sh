#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for abuild-rootbld (noarch meta-package)
# Verifies the runtime dependency contract for `abuild rootbld`.
set -euo pipefail

echo "[test] rootbld --version"
rootbld --version | head -1 || { echo "FAIL"; exit 1; }
echo "[test] bwrap present"
command -v bwrap >/dev/null || { echo "FAIL: bwrap not found"; exit 1; }
echo "OK"
echo "[test] envsubst present"
command -v envsubst >/dev/null || { echo "FAIL: envsubst not found"; exit 1; }
echo "OK"
echo "[test] abuild present"
command -v abuild >/dev/null || { echo "FAIL: abuild not found"; exit 1; }
echo "OK"
