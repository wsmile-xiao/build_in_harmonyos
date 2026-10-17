#!/bin/sh
# test_package/test.sh - pachi 12.9 consumer tests
# Three real cases against the installed pachi binary:
#   TC1: pachi --version reports 12.9/12.90 (non-empty, exit 0)
#   TC2: pachi --help lists options (non-empty, exit 0)
#   TC3: GTP genmove on 9x9 with =500 playouts returns '=' reply (real engine run)
set -u

PACHI_BIN="${1:-pachi}"

# Pachi resolves joseki/pattern data via $DATA_DIR (util.c get_data_file_:
# cwd -> $DATA_DIR -> exe dir). The package installs data to
# <prefix>/share/pachi-go, which is neither cwd nor exe dir here, so derive
# DATA_DIR from the binary path unless the caller already set it.
if [ -z "${DATA_DIR:-}" ]; then
  _bin_dir=$(dirname "$PACHI_BIN")
  DATA_DIR="$_bin_dir/../share/pachi-go"
  export DATA_DIR
fi

discovered=3
passed=0
failed=0

# TC1: version
out="$("$PACHI_BIN" --version 2>&1)"
rc=$?
if [ $rc -eq 0 ] && [ -n "$out" ]; then
  passed=$((passed + 1))
  echo "[ok] TC1: version ok ($out)"
else
  failed=$((failed + 1))
  echo "[fail] TC1: --version failed rc=$rc out=$out"
fi

# TC2: help
out="$("$PACHI_BIN" --help 2>&1)"
rc=$?
if [ $rc -eq 0 ] && [ -n "$out" ]; then
  passed=$((passed + 1))
  echo "[ok] TC2: help ok"
else
  failed=$((failed + 1))
  echo "[fail] TC2: --help failed rc=$rc"
fi

# TC3: real GTP genmove (failure oracle: stub exit-1 binary fails here)
# Upstream GJ_MINGAMES=500 (ownermap.h); -t =200 is rejected with
# "Error: minimum 500 playouts." so use =500.
gtp_in="boardsize 9
clear_board
genmove b
quit"
out=$(printf "%s\n" "$gtp_in" | "$PACHI_BIN" -d0 -t "=500" 2>&1)
rc=$?
case "$out" in
  *"="*)
    has_eq=1
    ;;
  *)
    has_eq=0
    ;;
esac
if [ $rc -eq 0 ] && [ "$has_eq" -eq 1 ] && [ -n "$out" ]; then
  passed=$((passed + 1))
  echo "[ok] TC3: GTP genmove ok"
else
  failed=$((failed + 1))
  echo "[fail] TC3: GTP genmove failed rc=$rc out=$out"
fi

if [ $failed -eq 0 ]; then
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
  exit 0
else
  echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
  exit 1
fi
