#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for optipng executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

# Test 1: binary executes and reports version
echo "[test] optipng --version"
optipng --version | grep -q "7.9.1" || {
    echo "FAIL: optipng --version did not report version 7.9.1"
    exit 1
}
echo "PASS: --version OK"

# Test 2: end-to-end PNG optimization
# Generate a tiny PNG image with python3, optimize it, verify output exists.
# NOTE: /tmp is read-only on OHOS — use $TMPDIR or $HOME/tmp for scratch.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/optipng-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

python3 - "$TESTDIR/test-in.png" <<'PYEOF'
import struct, sys, zlib

out = sys.argv[1]
W = H = 2
# Build IHDR
ihdr = struct.pack(b">IIBBBBB", W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
raw = b""
for y in range(H):
    raw += b"\x00"  # filter: none
    for x in range(W):
        raw += bytes((x * 80, y * 80, (x + y) * 80))
compressed = zlib.compress(raw)

def chunk(ctype, data):
    c = ctype + data
    return struct.pack(b">I", len(data)) + c + struct.pack(b">I", zlib.crc32(c) & 0xFFFFFFFF)

png = b"\x89PNG\r\n\x1a\n"
png += chunk(b"IHDR", ihdr)
png += chunk(b"IDAT", compressed)
png += chunk(b"IEND", b"")
open(out, "wb").write(png)
PYEOF

echo "[test] optipng -o2 $TESTDIR/test-in.png"
( cd "$TESTDIR" && optipng -o2 test-in.png )
test -s "$TESTDIR/test-in.png" || {
    echo "FAIL: optipng did not produce valid output"
    exit 1
}
echo "PASS: optimized PNG produced ($(wc -c < "$TESTDIR/test-in.png") bytes)"
