#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the ext4fuse executable.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely executes the packaged binary. Mounting is impossible on
# OHOS (no /dev/fuse), so both cases exercise real argument handling:
#   1. no arguments -> prints "Version:" + "Usage:" to stderr, exit 1
#      (by design, see fuse-main.c main()).
#   2. nonexistent disk image -> nonzero exit with an honest error
#      ("disk_open: ..." or "Failed to initialize logging").
set -euo pipefail

echo "[test] ext4fuse with no arguments prints usage and exits 1"
set +e
OUT="$(ext4fuse 2>&1)"
RC=$?
set -e
if [ "$RC" -ne 1 ]; then
  echo "FAIL: expected exit 1, got $RC"
  echo "$OUT"
  exit 1
fi
echo "$OUT" | grep -q "Usage:" || { echo "FAIL: missing Usage line"; echo "$OUT"; exit 1; }
echo "$OUT" | grep -q "Version:" || { echo "FAIL: missing Version line"; echo "$OUT"; exit 1; }
echo "OK: usage path works (exit=$RC)"

echo "[test] ext4fuse rejects a nonexistent disk image"
set +e
OUT2="$(ext4fuse /nonexistent-ext4fuse-test-disk 2>&1)"
RC2=$?
set -e
if [ "$RC2" -eq 0 ]; then
  echo "FAIL: expected nonzero exit for a bad disk image"
  exit 1
fi
echo "$OUT2" | grep -Eq "disk_open|Failed to initialize logging" || {
  echo "FAIL: unexpected error text"
  echo "$OUT2"
  exit 1
}
echo "OK: bad-disk path fails honestly (exit=$RC2)"

echo "ALL TESTS PASSED"
