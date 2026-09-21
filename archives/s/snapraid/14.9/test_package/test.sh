#!/bin/sh
# test_package/test.sh — consumer test for snapraid 14.9
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary — builds a tiny
# two-disk array with real files, then asserts real behavior via exit
# codes (set -eu) and greppable output.
set -eu

echo "[test] snapraid -V"
snapraid -V | grep -q "SnapRAID CLI v14.9"
echo "OK: version banner"

BASE="$(pwd)/consumer-array"
rm -rf "$BASE"
mkdir -p "$BASE/disk1" "$BASE/disk2"
echo "payload one" > "$BASE/disk1/hello1.txt"
echo "payload two" > "$BASE/disk2/hello2.txt"

# HMDFS (OHOS) rejects fallocate(); snapraid aborts parity pre-allocation
# without its own --test-skip-fallocate opt. The simulated disks share one
# filesystem, so --test-skip-device (upstream's own opt for test arrays)
# disables the different-device safety check.
SNAPRAID_FLAGS="--test-skip-device --test-skip-fallocate"

printf 'parity %s\ncontent %s\ndisk d1 %s\ndisk d2 %s\n' \
    "$BASE/parity" "$BASE/content.lst" "$BASE/disk1" "$BASE/disk2" \
    > "$BASE/snapraid.conf"

echo "[test] snapraid sync (compute parity from two disks)"
snapraid $SNAPRAID_FLAGS -c "$BASE/snapraid.conf" sync > "$BASE/sync.log"
test -s "$BASE/parity"
test -s "$BASE/content.lst"
echo "OK: parity and content written"

echo "[test] snapraid check (verify every block against parity)"
snapraid $SNAPRAID_FLAGS -c "$BASE/snapraid.conf" check > "$BASE/check.log"
echo "OK: check passed"

echo "[test] snapraid -a check (forced full verification)"
snapraid $SNAPRAID_FLAGS -c "$BASE/snapraid.conf" -a check > "$BASE/acheck.log"
echo "OK: forced check passed"

echo "[test] snapraid dup and list"
echo "payload one" > "$BASE/disk1/dup1.txt"
snapraid $SNAPRAID_FLAGS -c "$BASE/snapraid.conf" dup > "$BASE/dup.log"
snapraid $SNAPRAID_FLAGS -c "$BASE/snapraid.conf" list > "$BASE/list.log"
grep -q "hello1.txt" "$BASE/list.log"
grep -q "hello2.txt" "$BASE/list.log"
echo "OK: dup and list behave"

echo "[test] consumer test finished successfully"
