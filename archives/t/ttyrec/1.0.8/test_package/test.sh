#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ttyrec executables
# Compiles test.c, creates a minimal ttyrec recording, runs ttytime
set -euo pipefail

_TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$_TMPDIR"
TMPFILE="$_TMPDIR/ttyrec-test-$$.log"
trap 'rm -f "$TMPFILE" "${_TMPDIR}/test_prog"' EXIT

# Compile and run test.c to verify it works
echo "[step] compile and run test.c"
"${CC:-clang}" -o "$_TMPDIR/test_prog" "$(dirname "$0")/test.c"
"$_TMPDIR/test_prog" && echo "        [ok] test.c compiled and executed"

# Create a minimal ttyrec recording (2 records)
#
# File format defined by io.c read_header()/write_header() (ttyrec 1.0.8):
#   int buf[3];
#   fread(buf, sizeof(int), 3, fp);  // 3 x 4 bytes = 12 bytes per header
#   h->tv.tv_sec  = convert_to_little_endian(buf[0]);
#   h->tv.tv_usec = convert_to_little_endian(buf[1]);
#   h->len        = convert_to_little_endian(buf[2]);
#
# convert_to_little_endian() is a no-op on little-endian platforms (OHOS arm64).
# NOT htonl/ntohl — see io.c line 71-79.
#
# Record 1: tv_sec=1, tv_usec=0, len=5, data="hello"
# Record 2: tv_sec=3, tv_usec=0, len=5, data="world"
# Expected: ttytime outputs "2" (3 - 1 = 2 seconds elapsed)
printf '\x01\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00hello' > "$TMPFILE"
printf '\x03\x00\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00world' >> "$TMPFILE"

echo "[step] ttytime on test recording"
# ttytime prints: "<elapsed_seconds>\t<filename>"
# Expected output: "2" (tv_sec=3 minus tv_sec=1)
OUTPUT=$(ttytime "$TMPFILE")
ELAPSED=$(echo "$OUTPUT" | head -1 | awk '{print $1}')
echo "        ttytime output: $OUTPUT"
if [ "$ELAPSED" = "2" ]; then
    echo "        [ok] ttytime OK (elapsed=2, expected=2)"
else
    echo "        [fail] ttytime output mismatch (got=$ELAPSED, expected=2)"
    exit 1
fi
