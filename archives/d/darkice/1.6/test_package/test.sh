#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the darkice binary.
set -uo pipefail

# ── Test: binary executes and reports version ──
# darkice -h may return non-zero exit code; check output instead.
echo "[test] darkice -h"
output=$(darkice -h 2>&1) || true
echo "$output" | grep -q "DarkIce 1.6" || {
    echo "FAIL: darkice -h did not report 'DarkIce 1.6'"
    exit 1
}
echo "PASS: darkice binary installed and executable"
echo "ALL TESTS PASSED"
