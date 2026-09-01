#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for bossa executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] bossac -h smoke test"
# bossac -h exits non-zero (common CLI behavior), so check output instead of exit code
(bossac -h 2>&1 || true) | grep -q "BOSSA" || {
    echo "[fail] bossac -h did not produce expected output"
    exit 1
}
echo "[ok] bossac -h OK"
