#!/bin/sh
# lbzip2 2.5 — real functional consumer test (R34/L0c compliant).
# Runs the INSTALLED lbzip2/lbunzip2 binaries through a compress ->
# decompress -> byte-compare round trip on patterned data (~1 MiB).
# Exits non-zero on any wrong behavior (corruption, nonzero rc, mismatch).
set -u

LBIZIP2=""
for cand in lbzip2; do
    if command -v "$cand" >/dev/null 2>&1; then
        LBIZIP2=$(command -v "$cand")
        break
    fi
done
LBUNZIP2=""
for cand in lbunzip2 bunzip2; do
    if command -v "$cand" >/dev/null 2>&1; then
        LBUNZIP2=$(command -v "$cand")
        break
    fi
done

if [ -z "$LBIZIP2" ] || [ -z "$LBUNZIP2" ]; then
    echo "FAIL: lbzip2 binaries not found in PATH (lbzip2=${LBIZIP2:-none}, lbunzip2=${LBUNZIP2:-none})"
    exit 1
fi
echo "using: $LBIZIP2 / $LBUNZIP2"

TMPD=$(mktemp -d "${TMPDIR:-/tmp}/lbzip2-test.XXXXXX") || {
    echo "FAIL: cannot create temp dir"; exit 1; }
trap 'rm -rf "$TMPD"' EXIT HUP INT TERM

SRC="$TMPD/data.txt"
BZ2="$TMPD/data.txt.bz2"
OUT="$TMPD/out.txt"

# ~1 MiB of patterned data (exercises multi-threaded block pipeline)
i=0
while [ "$i" -lt 30000 ]; do
    printf 'The quick brown fox jumps over the lazy dog. 0123456789\n' >> "$SRC" || {
        echo "FAIL: cannot write source data"; exit 1; }
    i=$((i + 1))
done

# 1) compress with lbzip2
"$LBIZIP2" -v -1 -c "$SRC" > "$BZ2" || {
    echo "FAIL: lbzip2 compress exited $?"; exit 1; }
[ -s "$BZ2" ] || { echo "FAIL: compressed output empty"; exit 1; }

# 2) decompress with lbunzip2 (round trip)
"$LBUNZIP2" -c "$BZ2" > "$OUT" || {
    echo "FAIL: lbunzip2 decompress exited $?"; exit 1; }

# 3) byte-level integrity check
if cmp -s "$SRC" "$OUT"; then
    echo "PASS: round-trip byte-identical (src=$(wc -c < "$SRC") bytes)"
    exit 0
else
    echo "FAIL: decompressed output differs from source (src=$(wc -c < "$SRC"), out=$(wc -c < "$OUT"))"
    exit 1
fi