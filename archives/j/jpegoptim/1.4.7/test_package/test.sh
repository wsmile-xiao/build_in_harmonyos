#!/bin/sh
# test_package/test.sh - consumer test for the packaged jpegoptim binary.
#
# Usage: test.sh <jpegoptim_binary> <fixture.jpg>
#
# The fixture is a 16x16 baseline JPEG carrying a 16-byte COM (comment)
# segment, so both code paths are observable: lossless Huffman re-encoding
# must never grow the file, and --strip-all must remove the comment.
#
# 5 test cases; each prints "PASS: <name>" on success.

set -eu

BIN="$1"
SRC="$2"

size_of() {
    wc -c < "$1" | tr -d '[:space:]'
}

# /tmp is read-only on OHOS - keep the scratch tree under $HOME.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/jpegoptim-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT INT TERM

ORIG_SIZE=$(size_of "$SRC")
[ "$ORIG_SIZE" -gt 0 ] || { echo "FAIL: fixture is empty"; exit 1; }

# --- 1. version banner -------------------------------------------------
"$BIN" --version > "$TESTDIR/v.out" 2>&1
grep -q "1.4.7" "$TESTDIR/v.out" || { echo "FAIL: --version lacks 1.4.7"; cat "$TESTDIR/v.out"; exit 1; }
echo "PASS: version banner"

# --- 2. usage text (getopt_long + exit 0) ------------------------------
"$BIN" --help > "$TESTDIR/h.out" 2>&1 || { echo "FAIL: --help exited non-zero"; exit 1; }
grep -q "Usage:" "$TESTDIR/h.out" || { echo "FAIL: --help has no usage text"; exit 1; }
echo "PASS: usage text"

# --- 3. decode + report dimensions without touching the file -----------
cp "$SRC" "$TESTDIR/n.jpg"
"$BIN" -n -t "$TESTDIR/n.jpg" > "$TESTDIR/n.out" 2>&1
grep -q "n.jpg" "$TESTDIR/n.out" || { echo "FAIL: -n did not report the file"; cat "$TESTDIR/n.out"; exit 1; }
grep -q "16x16" "$TESTDIR/n.out" || { echo "FAIL: dimensions not decoded"; cat "$TESTDIR/n.out"; exit 1; }
grep -q "\[OK\]" "$TESTDIR/n.out" || { echo "FAIL: parser reported an error state"; cat "$TESTDIR/n.out"; exit 1; }
grep -qi "Average compression" "$TESTDIR/n.out" || { echo "FAIL: -t totals missing"; exit 1; }
NEW_SIZE=$(size_of "$TESTDIR/n.jpg")
[ "$NEW_SIZE" -eq "$ORIG_SIZE" ] || { echo "FAIL: -n (noaction) modified the file"; exit 1; }
echo "PASS: trial decode (16x16, [OK], totals, file untouched)"

# --- 4. lossless optimization in place ---------------------------------
cp "$SRC" "$TESTDIR/l.jpg"
"$BIN" -t "$TESTDIR/l.jpg" > "$TESTDIR/l.out" 2>&1
grep -qE "optimized|skipped" "$TESTDIR/l.out" || { echo "FAIL: no optimization verdict"; cat "$TESTDIR/l.out"; exit 1; }
NEW_SIZE=$(size_of "$TESTDIR/l.jpg")
[ "$NEW_SIZE" -le "$ORIG_SIZE" ] || { echo "FAIL: lossless run grew the file ($ORIG_SIZE -> $NEW_SIZE)"; exit 1; }
head -c 2 "$TESTDIR/l.jpg" | od -An -tx1 | grep -qi 'ff d8' || { echo "FAIL: SOI marker lost"; exit 1; }
tail -c 2 "$TESTDIR/l.jpg" | od -An -tx1 | grep -qi 'ff d9' || { echo "FAIL: EOI marker lost"; exit 1; }
echo "PASS: lossless optimize ($ORIG_SIZE -> $NEW_SIZE bytes, markers intact)"

# --- 5. --strip-all removes the embedded COM segment -------------------
cp "$SRC" "$TESTDIR/s.jpg"
"$BIN" --strip-all -t "$TESTDIR/s.jpg" > "$TESTDIR/s.out" 2>&1
grep -q "\[OK\]" "$TESTDIR/s.out" || { echo "FAIL: strip-all run errored"; cat "$TESTDIR/s.out"; exit 1; }
NEW_SIZE=$(size_of "$TESTDIR/s.jpg")
[ "$NEW_SIZE" -lt "$ORIG_SIZE" ] || { echo "FAIL: --strip-all did not shrink the file ($ORIG_SIZE -> $NEW_SIZE)"; exit 1; }
if LC_ALL=C grep -q "HarmonyOS PC" "$TESTDIR/s.jpg"; then
    echo "FAIL: comment segment survived --strip-all"
    exit 1
fi
tail -c 2 "$TESTDIR/s.jpg" | od -An -tx1 | grep -qi 'ff d9' || { echo "FAIL: stripped file lost EOI"; exit 1; }
echo "PASS: --strip-all drops COM segment ($ORIG_SIZE -> $NEW_SIZE bytes)"

echo "All tests passed."
