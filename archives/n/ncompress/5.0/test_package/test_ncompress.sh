#!/bin/sh
# ncompress smoke test from a consumer point of view.
# Verifies the packaged `compress` binary: version banner + round trip.
# Avoids cmp/diff (only POSIX sh + compress + printf + read are required).
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_ncompress.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
C="$BIN/compress"

[ -x "$C" ] || { echo "compress binary not found/executable: $C" >&2; exit 1; }
[ -x "$BIN/uncompress" ] || { echo "uncompress alias missing" >&2; exit 1; }
[ -x "$BIN/zcat" ] || { echo "zcat alias missing" >&2; exit 1; }

# Version banner (upstream prints '(N)compress 5.0')
"$C" -V >/dev/null 2>&1 || { echo "compress -V failed" >&2; exit 1; }

# Round trip: compress to stdout, decompress to stdout, compare content.
tmp="${TMPDIR:-/tmp}/nc_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

EXPECTED='the quick brown fox jumps over the lazy dog 0123456789'
printf '%s\n' "$EXPECTED" > "$tmp/in"

"$C" -c "$tmp/in" > "$tmp/in.Z" || { echo "compress -c failed" >&2; exit 1; }
[ -s "$tmp/in.Z" ] || { echo "compress produced empty output" >&2; exit 1; }

"$C" -d -c "$tmp/in.Z" > "$tmp/out" || { echo "compress -d -c failed" >&2; exit 1; }

read -r line < "$tmp/out"
if [ "$line" != "$EXPECTED" ]; then
    echo "round trip mismatch: got '$line'" >&2
    exit 1
fi

# uncompress alias decompresses an existing .Z back to the original file
cp "$tmp/in.Z" "$tmp/a.Z"
"$BIN/uncompress" "$tmp/a.Z" || { echo "uncompress alias failed" >&2; exit 1; }
read -r line2 < "$tmp/a"
[ "$line2" = "$EXPECTED" ] || { echo "uncompress round trip mismatch" >&2; exit 1; }

echo "ncompress smoke test OK"
