#!/bin/sh
# test_package consumer verification for winregfs 0.8.
#
# winregfs has no upstream automated test suite; its real entry points are the
# two installed binaries. This script drives them on a real, generated hive:
#
#   1. mount.winregfs -V              -> version banner, exit 0
#   2. fsck.winregfs (no arguments)   -> usage on stderr, exit 1
#   3. fsck.winregfs -v good.hiv      -> "Keys: 2  Values: 3 ... is clean", exit 0
#   4. fsck.winregfs -v bad.hiv       -> corruption reported, nonzero exit
#
# usage: test.sh <bindir>
set -u

BIN="${1:-.}"
FSCK="$BIN/fsck.winregfs"
MOUNT="$BIN/mount.winregfs"

fail=0
chk() { # $1=名称 $2=结果(0/1)
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

WORK="$(pwd)/winregfs-test-work"
rm -rf "$WORK"; mkdir -p "$WORK"

echo "--- winregfs consumer verification (bindir=$BIN) ---"

# 1. mount.winregfs version banner
out=$("$MOUNT" -V 2>&1); rc=$?
if [ "$rc" = "0" ] && echo "$out" | grep -q "Windows Registry Filesystem 0.8"; then r=0; else r=1; fi
chk "mount.winregfs -V -> [$out] (exit=$rc)" "$r"

# 2. fsck.winregfs without arguments prints usage and fails
out=$("$FSCK" 2>&1); rc=$?
if [ "$rc" != "0" ] && echo "$out" | grep -q "Usage:"; then r=0; else r=1; fi
chk "fsck.winregfs no-args usage (exit=$rc)" "$r"

# generate a structurally valid hive
PY=""
command -v python3 >/dev/null 2>&1 && PY=python3
[ -z "$PY" ] && command -v python >/dev/null 2>&1 && PY=python
if [ -z "$PY" ]; then echo "FAIL: no python interpreter for mkhive.py"; exit 1; fi
"$PY" mkhive.py "$WORK/good.hiv" >/dev/null || { echo "FAIL: hive generation"; exit 1; }

# 3. valid hive -> clean traversal
out=$("$FSCK" -v "$WORK/good.hiv" 2>&1); rc=$?
echo "$out" | grep -E "Keys:|is clean|errors"
if [ "$rc" = "0" ] && echo "$out" | grep -q "Keys: 2" \
   && echo "$out" | grep -q "Values: 3" && echo "$out" | grep -q "is clean"; then r=0; else r=1; fi
chk "fsck.winregfs -v good.hiv -> clean (exit=$rc)" "$r"

# 4. corrupted hive (bad 'regf' magic) -> errors reported
cp "$WORK/good.hiv" "$WORK/bad.hiv"
printf 'XXXX' | dd of="$WORK/bad.hiv" bs=1 seek=0 conv=notrunc status=none 2>/dev/null
out=$("$FSCK" -v "$WORK/bad.hiv" 2>&1); rc=$?
if [ "$rc" != "0" ] && echo "$out" | grep -q "total errors"; then r=0; else r=1; fi
chk "fsck.winregfs -v bad.hiv -> errors reported (exit=$rc)" "$r"

rm -rf "$WORK"
echo "test winregfs 0.8: $([ $fail = 0 ] && echo '4/4 PASS' || echo FAILED)"
exit $fail
