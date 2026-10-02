#! /bin/sh
# Manual driver for the mbr consumer tests; mirrors test_package/conanfile.py.
# Run from a writable directory with install-mbr on PATH:   sh test.sh
set -e

IMG=test-mbr.img
BEFORE=test-before.img
NOOP=test-noop.img
FORCED=test-force.img
SHORT=test-short.img

fail () { echo "FAIL: $*" >&2 ; exit 1 ; }

# 1./2. the binary is runnable and lists its options
install-mbr --version
# 输出重定向到文件后比对，避免管道提前退出造成 SIGPIPE
install-mbr --help > help.txt 2>&1 || fail "--help failed"
grep -q '^Usage:' help.txt || fail "no usage text"

# target: 510 zero bytes + the boot signature install-mbr expects
dd if=/dev/zero of=$IMG bs=512 count=1 2>/dev/null
printf '\125\252' | dd of=$IMG bs=1 seek=510 conv=notrunc 2>/dev/null
cp $IMG $BEFORE

# 3. install the boot record
install-mbr $IMG

# 4. still exactly one sector, signature kept
[ "$(wc -c < $IMG)" = "512" ] || fail "image size changed"
[ "$(dd if=$IMG bs=1 skip=510 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "55aa" ] \
  || fail "boot signature lost"

# 5. MBR code written into 0..439
dd if=$BEFORE of=code-before bs=1 count=440 2>/dev/null
dd if=$IMG of=code-after bs=1 count=440 2>/dev/null
cmp -s code-before code-after && fail "no MBR code was written"

# 6. partition table / disk signature area preserved
dd if=$BEFORE of=tab-before bs=1 skip=440 count=70 2>/dev/null
dd if=$IMG of=tab-after bs=1 skip=440 count=70 2>/dev/null
cmp tab-before tab-after || fail "partition table area was modified"

# 7. parameters can be read back
install-mbr -l $IMG > params.txt
for f in Version: Compatible: Drive: Timeout: ; do
  grep -q "$f" params.txt || fail "field $f missing from -l output"
done

# 8. -n (no-op) leaves the image untouched
cp $IMG $NOOP
install-mbr -n $NOOP
cmp $IMG $NOOP || fail "-n modified the image"

# 9. --force installs onto an image without a boot signature
dd if=/dev/zero of=$FORCED bs=512 count=1 2>/dev/null
install-mbr --force $FORCED
[ "$(dd if=$FORCED bs=1 skip=510 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "55aa" ] \
  || fail "--force did not install the boot record"

# 10. a target that is too short must be refused
: > $SHORT
if install-mbr $SHORT 2>/dev/null ; then
  fail "install-mbr accepted a 0 byte target"
fi

echo "mbr test_package: all checks passed"
