#!/data/service/hnp/bin/bash
# test_package/test.sh — compiles a consumer program against the installed
# header and runs it (R34: genuinely uses the tested package's API).
# Compile output goes to a temp dir so no artifacts land in the source tree.
set -euo pipefail

echo "[test] consumer compile with -I$PFD_INC"
CXX_BIN=clang++
command -v clang++ >/dev/null 2>&1 || CXX_BIN=c++
OUT="${TMPDIR:-$HOME/tmp}/pfd-test-$$"
mkdir -p "$OUT"
trap 'rm -rf "$OUT"' EXIT
"$CXX_BIN" -std=c++11 -I"$PFD_INC" test.cpp -o "$OUT/pfd_test"
echo "OK: header compiles standalone"

echo "[test] run consumer program (calls pfd public API)"
"$OUT/pfd_test"
echo "OK: API calls executed"

echo "ALL CONSUMER TESTS PASSED"
