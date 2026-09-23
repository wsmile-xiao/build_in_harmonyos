#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for sysstat executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

# sysstat uses -V for version (not --version)
echo "[step] sar -V"
sar -V && echo "        [ok] sar -V OK" || {
    echo "        [fail] sar -V failed"
    echo "FAIL: sysstat binary failed"
    exit 1
}
