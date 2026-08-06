#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for aaphoto executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

# Test 1: binary executes and reports version
echo "[test] aaphoto --version"
aaphoto --version | grep -q "0.45" || {
    echo "❌ aaphoto --version did not report version 0.45"
    exit 1
}
echo "✅ --version OK"

# Test 2: end-to-end image color correction
# Generate a tiny 2x2 24-bit BMP (no external deps beyond python3, which conan needs anyway)
# NOTE: /tmp is read-only on OHOS — use $HOME/tmp for the scratch dir.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/aaphoto-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

python3 - "$TESTDIR/test-in.bmp" <<'PYEOF'
import struct, sys
out = sys.argv[1]
W = H = 2
row_size = (W * 3 + 3) & ~3
pix = b""
for y in range(H):
    row = b""
    for x in range(W):
        row += bytes((x * 50, y * 50, (x + y) * 50))
    pix += row + b"\x00" * (row_size - W * 3)
data_size = len(pix)
file_size = 14 + 40 + data_size
bmp = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
bmp += struct.pack("<IiiHHIIiiII", 40, W, H, 1, 24, 0, data_size, 2835, 2835, 0, 0)
bmp += pix
open(out, "wb").write(bmp)
PYEOF

echo "[test] aaphoto --png $TESTDIR/test-in.bmp"
( cd "$TESTDIR" && aaphoto --png test-in.bmp )
test -s "$TESTDIR/test-in_new.png" || {
    echo "❌ aaphoto did not produce test-in_new.png"
    exit 1
}
echo "✅ processed image produced ($(wc -c < "$TESTDIR/test-in_new.png") bytes)"
