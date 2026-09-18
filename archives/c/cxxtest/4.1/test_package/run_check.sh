#!/data/service/hnp/bin/bash
# test_package/run_check.sh — runs the signed consumer test binary and
# asserts the CxxTest ErrorPrinter runner reports success ("OK!").
# Requires $1 = binary path.
set -euo pipefail

BIN="$1"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

"$BIN" > "$OUT/run.txt" 2>&1
cat "$OUT/run.txt"
grep -q "OK!" "$OUT/run.txt"
echo "OK: CxxTest ErrorPrinter runner reported all tests passed"
