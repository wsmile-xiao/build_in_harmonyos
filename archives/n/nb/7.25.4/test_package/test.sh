#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for nb executable
# Runs in conanrun env (PATH includes installed bin/)
#
# AI review (P2): version assertion must fail hard — no --help fallback that
# lets an incorrectly-installed version pass CI with exit 0.
# AI review (P3): set -euo pipefail per R25.
set -euo pipefail

echo "[test] nb --version"
output="$(nb --version 2>&1)"
echo "$output"
echo "$output" | grep -q "7.25.4" || {
    echo "❌ --version did not report 7.25.4 (output above); failing hard." >&2
    exit 1
}
echo "✅ --version OK"
