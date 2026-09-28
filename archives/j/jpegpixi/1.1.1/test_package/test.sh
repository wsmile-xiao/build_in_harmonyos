#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer-side smoke test for jpegpixi executable
# Upstream 1.1.1 ships no test suite (no tests/ dir, no TESTS in Makefile.am),
# so this exercises the real fix pipeline on a generated minimal JPEG (R34).
set -u

PASS=0
FAIL=0
ok() { echo "PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# conan test() may run with cwd=/ — never trust pwd for writable space (E002: /tmp is read-only)
WORK="${HOME}/tmp/jpx-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK" || exit 1

# Minimal 16x16 4:4:4 JFIF, all-zero DCT coefficients (neutral gray), see
# build_jpeg.py in the adaptation workspace for the generator.
printf '%s' '/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/xAAUAAEAAAAAAAAAAAAAAAAAAAAA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/AABEIABAAEAMBEQACEQADEQD/2gAMAwEAAgADAAA/AAAAAP/Z' | base64 -d > in.jpg
[ -s in.jpg ] && ok "test JPEG generated" || bad "test JPEG generation"

# 1. K0: main command responds to --help or --version with rc=0
if timeout 30 jpegpixi --help >/dev/null 2>&1; then
    ok "K0: jpegpixi --help rc=0"
elif timeout 30 jpegpixi --version >/dev/null 2>&1; then
    ok "K0: jpegpixi --version rc=0"
else
    bad "K0: jpegpixi answered neither --help nor --version with rc=0"
fi

# 2. Real single-pixel fix: SOURCE DEST [D:]X,Y
if timeout 60 jpegpixi in.jpg out1.jpg 5,4 >/dev/null 2>&1 && [ -s out1.jpg ]; then
    ok "single-pixel fix 5,4 rc=0, output non-empty"
else
    bad "single-pixel fix 5,4 failed"
fi

# 3. Output is a structurally complete JPEG (SOI ... EOI)
if [ -s out1.jpg ]; then
    head -c 2 out1.jpg | od -An -tx1 | grep -q "ff d8" && \
    tail -c 2 out1.jpg | od -An -tx1 | grep -q "ff d9" && \
    ok "output has SOI/EOI markers" || bad "output JPEG markers"
else
    bad "output missing, skip marker check"
fi

# 4. Real block fix (size S=2): syntax [D:]X,Y,S
if timeout 60 jpegpixi in.jpg out2.jpg 5,4,2 >/dev/null 2>&1 && [ -s out2.jpg ]; then
    ok "block fix 5,4,2 rc=0, output non-empty"
else
    bad "block fix 5,4,2 failed"
fi

# 5. Dimensions preserved after re-encode (SOF0 parse via python3)
python3 - "$WORK" <<'PYEOF' && ok "SOF dimensions preserved in.jpg == out1.jpg == out2.jpg" || bad "SOF dimension check"
import struct, sys
def size(p):
    d = open(p, 'rb').read()
    i = 2
    while i + 4 < len(d):
        if d[i] != 0xFF:
            i += 1
            continue
        m = d[i+1]
        if m in (0xD8, 0xD9, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        ln = struct.unpack('>H', d[i+2:i+4])[0]
        if 0xC0 <= m <= 0xC3:
            h, w = struct.unpack('>HH', d[i+5:i+9])
            return (w, h)
        i += 2 + ln
    return None
w = sys.argv[1]
a, b, c = size(w+'/in.jpg'), size(w+'/out1.jpg'), size(w+'/out2.jpg')
print('sizes:', a, b, c)
assert a and b and c and a == b == c, 'dimension mismatch'
PYEOF

# 6. Round-trip: output must be re-parseable by jpegpixi itself (fix another
#    pixel in out1.jpg) — proves the re-encoded output is a valid JPEG.
if timeout 60 jpegpixi out1.jpg out3.jpg 2,3 >/dev/null 2>&1 && [ -s out3.jpg ]; then
    ok "round-trip: jpegpixi re-parses its own output"
else
    bad "round-trip re-parse failed"
fi

echo "[result] PASS=$PASS FAIL=$FAIL"
[ "$FAIL" -eq 0 ]
