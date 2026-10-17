#!/data/service/hnp/bin/bash
# test_package/test.sh - jpegqs artifact verification.
# set -e guarantees that a "PASS <n>" line is printed only when the check in
# front of it actually succeeded, so the PASS count in the log equals
# assertion_count in MANIFEST.yml (rule4 three-way same-source).
set -eu
WORK="${1:-.}"
PKG="${2:?package folder required}"
cd "$WORK"

JPEGQS="$PKG/bin/jpegqs"
n=0
ok() { n=$((n+1)); echo "PASS $n - $1"; }

test -f "$JPEGQS"; test -x "$JPEGQS"
ok "jpegqs CLI installed and executable"

./makejpeg
test -s src.jpg
ok "reference libjpeg encoder produced src.jpg"

"$JPEGQS" -i 0 -q 3 -n 1 src.jpg out.jpg
ok "packaged CLI ran a real transcode and exited 0"

test -s out.jpg
ok "output JPEG created and non-empty"

head -c 2 out.jpg | od -An -tx1 | tr -d ' \n' | grep -q '^ffd8$'
ok "output starts with SOI marker ffd8"

tail -c 2 out.jpg | od -An -tx1 | tr -d ' \n' | grep -q '^ffd9$'
ok "output ends with EOI marker ffd9"

if cmp -s src.jpg out.jpg; then
    echo "FAIL - output is byte-identical to input, smoothing did nothing"
    exit 1
fi
ok "output differs from input (DCT coefficients were recovered and re-written)"

"$JPEGQS" -i 0 -q 5 -n 2 -o src.jpg out2.jpg
test -s out2.jpg
ok "second option path (-q 5 -n 2 -o) works"

test -f "$PKG/lib/libjpegqs.a"
ok "static library libjpegqs.a packaged"

test -f "$PKG/include/libjpegqs.h"
ok "public header libjpegqs.h packaged"

./consumer | grep -q 'do_quantsmooth resolved at 0x'
ok "consumer program links against packaged libjpegqs.a and runs"

test -f "$PKG/licenses/LICENSE"
ok "LICENSE packaged under licenses/"

echo "ALL_TESTS_PASSED=$n"
