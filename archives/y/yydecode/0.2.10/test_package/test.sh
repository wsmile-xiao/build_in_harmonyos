#!/data/service/hnp/bin/bash
# test_package/test.sh — substantive consumer test for the yydecode package.
#
# R34: genuinely runs the packaged yydecode binary and checks real decoded
# output (byte-for-byte) rather than only printing strings.
#
# Usage: test.sh <datadir>
set -euo pipefail

DATADIR="${1:-testdata}"

# Work inside the (writable) test_package build folder and always remove the
# scratch tree afterwards so the recipe directory stays pristine.
WORK="$(pwd)/yydecode-test-out"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "[test] yydecode --version"
yydecode --version | grep -F "yydecode 0.2.10"
echo "OK: --version reports yydecode 0.2.10"

rm -rf "$WORK"
mkdir -p "$WORK"

echo "[test] decode a yEnc stream to an explicit output file"
yydecode -o "$WORK/out.bin" "$DATADIR/sample.yenc"
cmp "$DATADIR/sample.bin" "$WORK/out.bin"
echo "OK: decoded bytes match the reference payload"

echo "[test] decode a yEnc stream to the file name embedded in the header"
( cd "$WORK" && yydecode "$DATADIR/sample.yenc" )
cmp "$DATADIR/sample.bin" "$WORK/sample.bin"
echo "OK: header-name decode also matches"

echo "[test] a stream with a corrupt CRC32 must be rejected and quarantined"
# Use a pristine directory: the output name comes from the stream header, and an
# already-present file would make yydecode bail out before verifying the CRC.
NEG="$WORK/negative"
mkdir -p "$NEG"
set +e
( cd "$NEG" && yydecode "$DATADIR/sample_badcrc.yenc" ) >/dev/null 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    echo "FAIL: yydecode accepted a stream with a bad CRC32"
    exit 1
fi
test -f "$NEG/sample.bin.broken"
echo "OK: bad CRC32 rejected (exit $rc); partial output quarantined as sample.bin.broken"

echo "[test] all yydecode package checks passed"
