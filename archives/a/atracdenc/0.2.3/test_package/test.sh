#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the atracdenc executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

echo "[test] atracdenc -h (help exits 0)"
atracdenc -h > /dev/null 2>&1 || {
    echo "❌ atracdenc -h failed"
    exit 1
}
echo "✅ -h OK"

# Test 2: end-to-end ATRAC3 encode.
# atracdenc accepts only 44100 Hz 16-bit WAV input (CheckInputFormat).
# Generate a 0.25 s mono WAV with python3 (present on the OHOS device).
# NOTE: /tmp is read-only on OHOS — use $TMPDIR/$HOME/tmp for scratch space.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/atracdenc-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

python3 - "$TESTDIR/in.wav" <<'PYEOF'
import struct, sys
out = sys.argv[1]
rate = 44100
channels = 1
bits = 16
frames = rate // 4  # 0.25 s
data = b"\x00\x00" * frames
hdr = struct.pack("<4sI4s", b"RIFF", 36 + len(data), b"WAVE")
hdr += struct.pack("<4sIHHIIHH", b"fmt ", 16, 1, channels, rate,
                   rate * channels * bits // 8, channels * bits // 8, bits)
hdr += struct.pack("<4sI", b"data", len(data))
open(out, "wb").write(hdr + data)
PYEOF

echo "[test] atracdenc -e atrac3 -i in.wav -o out.oma"
( cd "$TESTDIR" && atracdenc -e atrac3 -i in.wav -o out.oma )
test -s "$TESTDIR/out.oma" || {
    echo "❌ ATRAC3 encode produced no non-empty out.oma"
    exit 1
}
echo "✅ ATRAC3 encode OK ($(wc -c < "$TESTDIR/out.oma") bytes)"
