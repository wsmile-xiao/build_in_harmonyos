#!/bin/sh
# test_package/test.sh — functional consumer test for myrescue 0.9.8
#
# Usage: test.sh <bin_dir> <work_dir>
#
# R34/R51: this is not a `--version` stamp.  myrescue's whole job is "read a
# damaged source block by block, write the recoverable blocks to a target and
# keep a per-block health bitmap", and it works on ordinary files just as well
# as on block devices — so every assertion runs one of the three installed
# binaries against real data and checks the real outcome: the recovered bytes,
# the bitmap encoding, and what the two bitmap inspectors derive from it.
#
# POSIX sh only (the target has no /bin/bash; the runner picks hnp bash when
# present and falls back to /bin/sh).  Deliberately avoids the variable names
# LINES/COLUMNS, which ash-family shells host internally.

BIN_DIR="$1"
WORK="$2"
[ -n "$BIN_DIR" ] || { echo "FATAL: no bin dir given"; exit 2; }
[ -n "$WORK" ] || { echo "FATAL: no work dir given"; exit 2; }

MYRESCUE="$BIN_DIR/myrescue"
STAT="$BIN_DIR/myrescue-stat"
BMP2PPM="$BIN_DIR/myrescue-bitmap2ppm"

BLOCK=1024
NBLK=8
SRC_SIZE=$((BLOCK * NBLK))

TOTAL=0
PASSED=0
FAILED=0

pass() { TOTAL=$((TOTAL + 1)); PASSED=$((PASSED + 1)); echo "PASS: $1"; }
fail() { TOTAL=$((TOTAL + 1)); FAILED=$((FAILED + 1)); echo "FAIL: $1"; }
eq() { if [ "$2" = "$3" ]; then pass "$1"; else fail "$1 (expected [$2] got [$3])"; fi; }
ne() { if [ "$2" != "$3" ]; then pass "$1"; else fail "$1 (value must not be [$3])"; fi; }
rc0() { if [ "$2" = "0" ]; then pass "$1"; else fail "$1 (exit status $2)"; fi; }
rcn() { if [ "$2" != "0" ]; then pass "$1"; else fail "$1 (exit status must be non-zero)"; fi; }

file_size() { wc -c "$1" | awk '{print $1}'; }
hexof() { od -An -tx1 -v "$1" | tr -d ' \n'; }
readout() { sed 's/\r//g' "$1"; }
repeat() { i=0; R=""; while [ "$i" -lt "$2" ]; do R="$R$1"; i=$((i + 1)); done; printf '%s' "$R"; }
# P6 headers are not fixed-width (the geometry line depends on the requested
# width), so the pixel body offset has to be derived, never assumed.
body_off() { awk 'NR<=3{o+=length($0)+1} NR==3{print o+0; exit}' "$1"; }
# pixel <ppm-file> <index> -> "r g b"
pixel() {
    off=$(body_off "$1")
    od -An -tu1 -v -j $((off + $2 * 3)) -N 3 "$1" | tr -s ' ' | sed 's/^ *//'
}

rm -rf "$WORK"
mkdir -p "$WORK" || { echo "FATAL: cannot create work dir"; exit 2; }
cd "$WORK" || { echo "FATAL: cannot enter work dir"; exit 2; }

echo "===== [0] installed artifacts ====="
for b in myrescue myrescue-stat myrescue-bitmap2ppm; do
    if [ -x "$BIN_DIR/$b" ]; then pass "bin/$b installed and executable"; else fail "bin/$b missing or not executable"; fi
done
for p in myrescue.1 myrescue-stat.1 myrescue-bitmap2ppm.1; do
    if [ -f "$BIN_DIR/../share/man/man1/$p" ]; then pass "man1/$p installed"; else fail "man1/$p missing"; fi
done
if [ -f "$BIN_DIR/../share/man/de/man1/myrescue.1" ]; then
    pass "upstream German page installed as de/man1/myrescue.1"
else
    fail "de/man1/myrescue.1 missing"
fi

echo "===== [1] clean file -> file recovery ====="
head -c "$SRC_SIZE" /dev/urandom > src1.bin
"$MYRESCUE" -b "$BLOCK" src1.bin dst1.bin >run1.out 2>run1.err
rc0 "myrescue exits 0 on a healthy source" $?
if [ -f dst1.bin ]; then pass "target file created"; else fail "target file not created"; fi
eq "recovered size equals source size" "$SRC_SIZE" "$(file_size dst1.bin)"
if cmp -s src1.bin dst1.bin; then pass "recovered bytes are byte-identical to source"; else fail "recovered bytes differ from source"; fi

echo "----- block bitmap written by [1]"
if [ -f dst1.bin.bitmap ]; then pass "default bitmap <target>.bitmap created"; else fail "default bitmap <target>.bitmap missing"; fi
eq "bitmap holds exactly one byte per block" "$NBLK" "$(file_size dst1.bin.bitmap)"
eq "every block recorded as good (0x01)" "$(repeat 01 "$NBLK")" "$(hexof dst1.bin.bitmap)"

echo "----- myrescue-stat on [1]"
"$STAT" dst1.bin.bitmap >stat1.out 2>stat1.err
rc0 "myrescue-stat exits 0" $?
eq "myrescue-stat reports 8 good blocks at 100%" "1: 8 (100.00%)" "$(readout stat1.out)"

echo "----- myrescue-bitmap2ppm on [1]"
"$BMP2PPM" dst1.bin.bitmap "$NBLK" >pic1.ppm 2>pic1.err
rc0 "myrescue-bitmap2ppm exits 0" $?
eq "PPM magic is P6" "P6" "$(sed -n '1p' pic1.ppm)"
eq "PPM geometry is <blocks> x 1" "$NBLK 1" "$(sed -n '2p' pic1.ppm)"
eq "PPM maxval is 255" "255" "$(sed -n '3p' pic1.ppm)"
eq "PPM carries 3 bytes per block after the header" \
   "$(( $(body_off pic1.ppm) + NBLK * 3 ))" "$(file_size pic1.ppm)"
eq "pixel 0 is green (0 128 0) = recovered block" "0 128 0" "$(pixel pic1.ppm 0)"
eq "pixel 7 is green (0 128 0) = recovered block" "0 128 0" "$(pixel pic1.ppm $((NBLK - 1)))"

echo "===== [2] damaged tail: unreadable blocks are recorded, not lost ====="
# Requesting blocks past the readable end stands in for a damaged surface:
# myrescue must still recover the readable prefix and record the rest.
rm -f dst2.bin dst2.bin.bitmap
"$MYRESCUE" -b "$BLOCK" -e 12 src1.bin dst2.bin >run2.out 2>run2.err
rc0 "myrescue survives an unreadable tail" $?
eq "readable prefix still fully recovered" "$SRC_SIZE" "$(file_size dst2.bin)"
if cmp -s src1.bin dst2.bin; then pass "recovered prefix byte-identical despite later failures"; else fail "recovered prefix corrupted by later failures"; fi
eq "bitmap records 8 good (01) then 4 failed (ff)" \
   "$(repeat 01 "$NBLK")$(repeat ff 4)" "$(hexof dst2.bin.bitmap)"
"$STAT" dst2.bin.bitmap >stat2.out 2>&1
eq "myrescue-stat separates failed from good" \
   "-1: 4 (33.33%)
1: 8 (66.67%)" "$(readout stat2.out)"

echo "----- failed blocks must render as the 'failed' colour, not 'unexamined'"
"$BMP2PPM" dst2.bin.bitmap 12 >pic2.ppm 2>pic2.err
eq "bitmap2ppm accepts the mixed bitmap" "12 1" "$(sed -n '2p' pic2.ppm)"
eq "failed block 8 renders yellow (255 255 0)" "255 255 0" "$(pixel pic2.ppm 8)"
eq "good block 0 still renders green (0 128 0)" "0 128 0" "$(pixel pic2.ppm 0)"

echo "===== [3] signedness regression guard: failed blocks get retried ====="
# myrescue's promise is to leave a damaged area and *come back*.  Coming back
# is decided by comparing the plain-char bitmap value against 0 and -127, which
# only behaves correctly when plain char is signed on the target.  Probe: a
# block unreadable in pass 1 becomes readable in pass 2 — pass 2 must then
# actually recover it.
rm -rf resume && mkdir -p resume && cd resume
head -c "$SRC_SIZE" /dev/urandom > rsrc.bin
"$MYRESCUE" -b "$BLOCK" -e 12 rsrc.bin rout.bin >r1.out 2>&1
if [ -f rout.bin.bitmap ]; then pass "resume probe pass 1 wrote a bitmap"; else fail "resume probe pass 1 wrote no bitmap"; fi
eq "resume probe pass 1 marks the tail failed" \
   "$(repeat 01 "$NBLK")$(repeat ff 4)" "$(hexof rout.bin.bitmap)"
head -c "$BLOCK" /dev/urandom >> rsrc.bin
head -c "$BLOCK" /dev/urandom >> rsrc.bin
head -c "$BLOCK" /dev/urandom >> rsrc.bin
head -c "$BLOCK" /dev/urandom >> rsrc.bin
"$MYRESCUE" -b "$BLOCK" -e 12 rsrc.bin rout.bin >r2.out 2>&1
eq "myrescue returns to blocks that failed earlier (bitmap cleared to 01)" \
   "$(repeat 01 12)" "$(hexof rout.bin.bitmap)"
eq "the return pass recovered the whole surface" "$((BLOCK * 12))" "$(file_size rout.bin)"
if cmp -s rsrc.bin rout.bin; then pass "recovered surface byte-identical after retry"; else fail "recovered surface differs after retry"; fi
cd "$WORK"

echo "===== [4] explicit bitmap path, partial range, abort mode ====="
rm -f dst4.bin mycustom.bmap dst4.bin.bitmap
"$MYRESCUE" -b "$BLOCK" -B mycustom.bmap src1.bin dst4.bin >run4.out 2>&1
if [ -f mycustom.bmap ] && [ ! -f dst4.bin.bitmap ]; then pass "-B honours an explicit bitmap path"; else fail "-B did not control the bitmap path"; fi
rm -f dst5.bin dst5.bin.bitmap
"$MYRESCUE" -b "$BLOCK" -s 2 -e 5 src1.bin dst5.bin >run5.out 2>&1
eq "-s/-e copy only the requested range" "0000010101" "$(hexof dst5.bin.bitmap)"
"$STAT" dst5.bin.bitmap >stat5.out 2>&1
eq "untouched blocks stay class 0, copied blocks class 1" \
   "0: 2 (40.00%)
1: 3 (60.00%)" "$(readout stat5.out)"
rm -f dst6.bin dst6.bin.bitmap
"$MYRESCUE" -b "$BLOCK" -A -e 12 src1.bin dst6.bin >run6.out 2>&1
eq "-A stops at the first failing block" "$(repeat 01 "$NBLK")ff" "$(hexof dst6.bin.bitmap)"

echo "===== [5] random-jump mode (exercises the permute() path) ====="
rm -f dst7.bin dst7.bin.bitmap
"$MYRESCUE" -b "$BLOCK" -J 3 src1.bin dst7.bin >run7.out 2>&1
rc0 "-J run completes" $?
if cmp -s src1.bin dst7.bin; then pass "-J out-of-order pass still reconstructs the source exactly"; else fail "-J corrupted the reconstruction"; fi

echo "===== [6] argument handling ====="
"$MYRESCUE" -h >usage.out 2>&1
if grep -qF 'myrescue [<options>]' usage.out; then pass "-h prints the usage synopsis"; else fail "-h printed no usage synopsis"; fi
"$MYRESCUE" -b 0 src1.bin dstx.bin >badbs.out 2>&1
rcn "invalid block size is refused" $?
if grep -qF 'invalid block-size' badbs.out; then pass "invalid block size names the option"; else fail "invalid block size gave no diagnostic"; fi
"$MYRESCUE" >noargs.out 2>&1
rcn "bare invocation is refused" $?

echo
echo "ASSERTION TOTAL=$TOTAL PASSED=$PASSED FAILED=$FAILED"
if [ "$FAILED" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
exit 0
