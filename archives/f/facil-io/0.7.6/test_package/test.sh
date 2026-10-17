#!/data/service/hnp/bin/bash
# test_package/test.sh — compiles a consumer HTTP server/client program
# against the installed facil.io library and runs it (R34).
# Compile output goes to a temp dir so no artifacts land in the source tree.
set -euo pipefail

# facil.io cluster socket binds under TMPDIR; /tmp is read-only on OHOS
export TMPDIR="${TMPDIR:-$HOME/tmp}"

INC_FLAGS=""
IFS=';' read -ra DIRS <<< "$FIO_INCS"
for d in "${DIRS[@]}"; do
  INC_FLAGS="$INC_FLAGS -I$d"
done

echo "[test] consumer compile against installed facil.io"
CC_BIN=clang
command -v clang >/dev/null 2>&1 || CC_BIN=cc
OUT="${TMPDIR:-$HOME/tmp}/facil-test-$$"
mkdir -p "$OUT"
trap 'rm -rf "$OUT"' EXIT
"$CC_BIN" $INC_FLAGS test.c -o "$OUT/facil_test" -L"$FIO_LIB" -lfacil -lpthread -lm
echo "OK: consumer program links against libfacil"

echo "[test] run in-process HTTP server/client loop"
"$OUT/facil_test"
echo "OK: HTTP round trip served"

echo "ALL CONSUMER TESTS PASSED"
