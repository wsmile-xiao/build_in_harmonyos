#!/bin/sh
# xdms 1.3.2 consumer smoke test.
#
# The DMS fixture is GENERATED AT TEST TIME by make_sample_dms.py (plain Python
# source, standard library only).  Nothing binary is committed: a committed
# blob cannot travel inside GitCode's /pull/<n>.diff, which is what the CI
# applies at its checkout-pr step, and carrying one made that step fail with
#     error: missing binary patch data for '.../sample.dms'
#
# The generated archive contains one uncompressed ("NOCOMP") track of 3000
# bytes, so the decode below exercises the complete unpack path — main-header
# CRC, track-header CRC, packed-data CRC, unpack, post-unpack checksum and the
# output write — not a stub.  The expected payload is regenerated here from the
# same 63-byte line the generator uses, so the comparison is independent of the
# generator's own bytes.
#
# Requires only POSIX sh + python3 + printf/head/cmp/grep/dd.
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_xdms.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
X="$BIN/xdms"
HERE=$(dirname "$0")

# --- 1: packaged binary exists and is executable -----------------------------
[ -x "$X" ] || { echo "xdms binary not found/executable: $X" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/xdms_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

SAMPLE="$tmp/sample.dms"

# --- 2: the DMS fixture can be generated from text (no binary in the repo) ---
python3 "$HERE/make_sample_dms.py" "$SAMPLE" > /dev/null || {
    echo "make_sample_dms.py failed to generate the fixture" >&2; exit 1; }
[ -s "$SAMPLE" ] || { echo "generated fixture is empty" >&2; exit 1; }

# --- 3: no arguments -> usage screen and non-zero exit -----------------------
if "$X" >/dev/null 2>&1; then
    echo "xdms with no arguments should have failed" >&2
    exit 1
fi

# --- 4: archive integrity test on a valid archive ----------------------------
"$X" t "$SAMPLE" > "$tmp/t.out" 2>&1 || {
    echo "xdms t failed on a valid fixture" >&2; cat "$tmp/t.out" >&2; exit 1; }

# --- 5: integrity output says the archive is ok ------------------------------
grep -q 'is ok' "$tmp/t.out" || {
    echo "xdms t did not report the archive as ok:" >&2; cat "$tmp/t.out" >&2; exit 1; }

# --- 6/7: metadata view succeeds and reports the NOCOMP mode -----------------
"$X" v "$SAMPLE" > "$tmp/v.out" 2>&1 || {
    echo "xdms v failed" >&2; cat "$tmp/v.out" >&2; exit 1; }
grep -q 'NOCOMP' "$tmp/v.out" || {
    echo "xdms v did not report NOCOMP:" >&2; cat "$tmp/v.out" >&2; exit 1; }

# --- 8: a real decode completes ----------------------------------------------
"$X" u "$SAMPLE" "+$tmp/out.bin" > "$tmp/u.out" 2>&1 || {
    echo "xdms u failed to decode the fixture" >&2; cat "$tmp/u.out" >&2; exit 1; }

# --- 9: the decoded image exists ---------------------------------------------
[ -f "$tmp/out.bin" ] || { echo "xdms u produced no output image" >&2; exit 1; }

# --- 10: decoded size matches the archive's unpacked size --------------------
sz=$(wc -c < "$tmp/out.bin" | tr -d ' ')
[ "$sz" = "3000" ] || { echo "decoded size $sz != expected 3000" >&2; exit 1; }

# --- 11: decode a corrupted-track archive, expect non-zero -------------------
cp "$SAMPLE" "$tmp/corrupt.dms"
printf '\377' | dd of="$tmp/corrupt.dms" bs=1 seek=200 conv=notrunc 2>/dev/null
if "$X" t "$tmp/corrupt.dms" >/dev/null 2>&1; then
    echo "xdms t accepted an archive with a corrupted track CRC" >&2
    exit 1
fi

# --- 12: a non-DMS file must be rejected -------------------------------------
printf 'not a dms archive\n' > "$tmp/bogus.dms"
if "$X" t "$tmp/bogus.dms" >/dev/null 2>&1; then
    echo "xdms t accepted a non-DMS file" >&2
    exit 1
fi

# --- 13: decoded bytes are byte-identical to independently built expected data
i=0
while [ "$i" -lt 48 ]; do
    printf '%s\n' '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    i=$((i + 1))
done | head -c 3000 > "$tmp/expected.bin"
[ -s "$tmp/expected.bin" ] || { echo "failed to build expected data" >&2; exit 1; }

"$X" u "$SAMPLE" "+$tmp/cmp.bin" >/dev/null 2>&1 || {
    echo "second decode failed" >&2; exit 1; }
cmp -s "$tmp/cmp.bin" "$tmp/expected.bin" || {
    echo "decoded bytes differ from expected payload" >&2; exit 1; }

echo "xdms smoke test OK (fixture/usage/integrity/view/decode/negative paths)"
