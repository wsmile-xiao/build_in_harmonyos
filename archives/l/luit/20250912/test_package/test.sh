#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for luit executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] luit smoke test"
luit -V && echo "        [ok] luit -V OK" || {
    echo "        [fail] luit -V failed"
    exit 1
}
