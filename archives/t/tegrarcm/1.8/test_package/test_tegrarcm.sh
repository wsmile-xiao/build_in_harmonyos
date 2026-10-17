#!/bin/sh
# test_tegrarcm.sh <binary> <workdir>
# Consumer smoke test for the packaged tegrarcm binary (4 real assertions).
# Design notes:
# - tegrarcm --version exits 0 and prints "tegrarcm 1.8" to stdout.
# - tegrarcm --help prints usage to stderr and exits 1 (EXIT_FAILURE upstream).
#   Asserting rc!=0 plus non-empty "usage" output proves the real binary runs:
#   an `exit 0` stub would fail assertion 3.
# - All outputs must be non-empty (toybox lesson: empty-vs-empty comparison
#   can fake a pass). Every assertion checks content, not just exit codes.
# - Emits deterministic trailer: RESULT: P passed, F failed
set -eu
BIN="$1"
WORK="$2"
PASS=0
FAIL=0
ok() { PASS=$((PASS+1)); echo "PASS: $1"; }
bad() { FAIL=$((FAIL+1)); echo "FAIL: $1"; }

# 1. binary present and executable
if [ -x "$BIN" ]; then ok "binary executable: $BIN"; else bad "binary not executable: $BIN"; fi

# 2. --version: rc 0, non-empty, contains 1.8
VOUT="$WORK/version.out"
if "$BIN" --version >"$VOUT" 2>&1; then
  if [ -s "$VOUT" ] && grep -q "1\.8" "$VOUT"; then ok "--version prints 1.8 ($(cat "$VOUT"))"; else bad "--version output missing 1.8 or empty"; fi
else
  bad "--version exited non-zero"
fi

# 3. --help: rc non-zero (upstream EXIT_FAILURE), output non-empty with usage
HOUT="$WORK/help.out"
if "$BIN" --help >"$HOUT" 2>&1; then HRC=0; else HRC=$?; fi
if [ "$HRC" -ne 0 ] && [ -s "$HOUT" ] && grep -qi "usage" "$HOUT"; then ok "--help usage banner (rc=$HRC)"; else bad "--help unexpected (rc=$HRC, size=$(wc -c <"$HOUT"))"; fi

# 4. no-args: must fail with BCT hint (proves arg validation runs)
NOUT="$WORK/noargs.out"
if "$BIN" >"$NOUT" 2>&1; then NRC=0; else NRC=$?; fi
if [ "$NRC" -ne 0 ] && [ -s "$NOUT" ] && grep -q "BCT" "$NOUT"; then ok "no-args validation (rc=$NRC)"; else bad "no-args unexpected (rc=$NRC)"; fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
