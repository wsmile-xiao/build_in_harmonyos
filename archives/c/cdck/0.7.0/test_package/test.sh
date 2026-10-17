#!/bin/sh
# test_package/test.sh — functional test for the cdck executable.
# cdck measures real CD/DVD hardware via linux/cdrom.h ioctls; no optical
# drive exists in the OHOS build/CI sandbox, so we verify the real binary
# on its hardware-free and fast-failing paths (4 cases):
#   1. binary is present and executable
#   2. `cdck -V` prints the 0.7.0 version and exits 0
#   3. `cdck -h` prints Usage and exits 0
#   4. `cdck -d /dev/nonexistent-...` fails fast reading the TOC (exit != 0)
set -u

BIN="$1"
PASS=0
FAIL=0

echo "[test] cdck: locate binary"
if [ -z "$BIN" ]; then
  BIN="$(command -v cdck || true)"
fi
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
  echo "FAIL: cdck binary not found (arg='$1')"
  exit 1
fi
if [ ! -x "$BIN" ]; then
  echo "FAIL: $BIN not executable"
  exit 1
fi
PASS=$((PASS + 1))
echo "[ok] binary at $BIN"

echo "[test] cdck -V prints version"
set +e
OUT="$("$BIN" -V 2>&1)"
RC=$?
set -e
echo "  exit=$RC out=$OUT"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: cdck -V exited $RC"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "0\.7\.0"; then
  echo "FAIL: cdck -V output missing 0.7.0: $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] version output verified"
fi

echo "[test] cdck -h prints usage"
set +e
OUT="$("$BIN" -h 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -ne 0 ]; then
  echo "FAIL: cdck -h exited $RC"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "Usage:"; then
  echo "FAIL: cdck -h output missing Usage section: $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] help output verified"
fi

echo "[test] cdck bad device fails fast with TOC error"
set +e
OUT="$("$BIN" -d /dev/nonexistent-cdck-test-device 2>&1)"
RC=$?
set -e
echo "  exit=$RC"
if [ "$RC" -eq 0 ]; then
  echo "FAIL: expected non-zero exit for missing device"
  FAIL=$((FAIL + 1))
elif ! printf '%s' "$OUT" | grep -q "Unable to read TOC"; then
  echo "FAIL: expected TOC error message, got: $OUT"
  FAIL=$((FAIL + 1))
else
  PASS=$((PASS + 1))
  echo "[ok] bad-device error path verified"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"sh test.sh <installed bin/cdck>\",\"discovered\":4,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
  echo "[fail] $FAIL case(s) failed, $PASS passed"
  exit 1
fi
echo "[ok] all $PASS test_package cases passed"
