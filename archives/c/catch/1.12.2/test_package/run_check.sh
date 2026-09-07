#!/data/service/hnp/bin/bash
# test_package/run_check.sh — runs the signed consumer test binary and
# asserts the Catch runner reports success. Requires $1 = binary path.
set -euo pipefail

BIN="$1"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

"$BIN" > "$OUT/run.txt" 2>&1
cat "$OUT/run.txt"
grep -q "All tests passed" "$OUT/run.txt"
echo "OK: Catch runner reported all tests passed"
