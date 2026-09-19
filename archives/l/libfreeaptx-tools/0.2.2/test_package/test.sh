#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for freeaptxenc / freeaptxdec.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

for tool in freeaptxenc freeaptxdec; do
    command -v "$tool" >/dev/null || { echo "$tool is not on PATH"; exit 1; }
    echo "        [ok] $tool found on PATH"
done

# 1) --version / --help contract (patch 0002).  Upstream only knew -h/--help,
#    printed the usage text to stderr and returned 1 for it; -h was return 1 as
#    well and every unknown option landed in the same "return 1" default
#    branch, so the platform L2 smoke test could never see exit status 0.
for tool in freeaptxenc freeaptxdec; do
    echo "[test] $tool --version"
    VERSION_OUT="$("$tool" --version)"
    case "$VERSION_OUT" in
        *0.2.2*) echo "        [ok] $VERSION_OUT" ;;
        *) echo "$tool --version did not report 0.2.2: $VERSION_OUT"; exit 1 ;;
    esac
    echo "[test] $tool --help"
    "$tool" --help >/dev/null 2>&1
    echo "        [ok] --help exit status 0"
done
echo "[test] freeaptxenc -V"
freeaptxenc -V >/dev/null
echo "        [ok] -V exit status 0"

# 2) Regression guard for patch 0001: the tools must not need libfreeaptx.so.
#    Upstream linked them against the shared library, so a tools-only package
#    (which deletes lib/) would die with exit 127 "cannot open shared object
#    file: libfreeaptx.so.0" before --version could answer.
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    echo "[test] dynamic section must not reference libfreeaptx"
    if "$READELF" -d "$(command -v freeaptxenc)" 2>/dev/null | grep -q 'libfreeaptx'; then
        echo "freeaptxenc still has a DT_NEEDED entry for libfreeaptx"
        exit 1
    fi
    echo "        [ok] freeaptxenc is self-contained"
fi

# /tmp is read-only on OHOS - use a scratch dir under $HOME instead.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/libfreeaptx-tools-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# 3) 4800 bytes of 24 bit signed stereo PCM (800 frames = 200 aptX blocks),
#    generated with the Python standard library only.
echo "[test] generate 24 bit stereo PCM input"
python3 - "$TESTDIR/in.raw" <<'PYEOF'
import math
import sys

frames = 800
data = bytearray()
for n in range(frames):
    left = int(1000000 * math.sin(2 * math.pi * 440 * n / 44100))
    right = int(1000000 * math.sin(2 * math.pi * 554 * n / 44100))
    for value in (left, right):
        data += (value & 0xFFFFFF).to_bytes(3, "little")
with open(sys.argv[1], "wb") as f:
    f.write(bytes(data))
PYEOF
IN_SIZE=$(wc -c < "$TESTDIR/in.raw")
[ "$IN_SIZE" -eq 4800 ] || { echo "unexpected input size: $IN_SIZE"; exit 1; }
echo "        [ok] $IN_SIZE bytes of input"

# 4) aptX round trip.  800 frames = 200 blocks x 4 bytes, plus the 92 frame
#    (23 block) flush that aptx_encode_finish() appends.
echo "[test] freeaptxenc < in.raw > out.aptx"
freeaptxenc < "$TESTDIR/in.raw" > "$TESTDIR/out.aptx"
APT_X_SIZE=$(wc -c < "$TESTDIR/out.aptx")
[ "$APT_X_SIZE" -eq 892 ] || { echo "unexpected aptX size: $APT_X_SIZE (want 892)"; exit 1; }
echo "        [ok] $APT_X_SIZE bytes of aptX (800 + 92 flush)"

echo "[test] freeaptxdec < out.aptx > dec.raw"
freeaptxdec < "$TESTDIR/out.aptx" > "$TESTDIR/dec.raw"
DEC_SIZE=$(wc -c < "$TESTDIR/dec.raw")
[ "$DEC_SIZE" -eq "$IN_SIZE" ] || {
    echo "aptX round trip changed the PCM size: $IN_SIZE -> $DEC_SIZE"; exit 1
}
echo "        [ok] decoded back to $DEC_SIZE bytes"

python3 - "$TESTDIR/in.raw" "$TESTDIR/dec.raw" <<'PYEOF'
import sys


def samples(path):
    data = open(path, "rb").read()
    out = []
    for i in range(0, len(data) - 2, 3):
        value = int.from_bytes(data[i:i + 3], "little")
        if value >= 1 << 23:
            value -= 1 << 24
        out.append(value)
    return data, out


raw_in, in_values = samples(sys.argv[1])
raw_out, out_values = samples(sys.argv[2])
assert raw_in != raw_out, "decoded stream is bit identical to the input - not a codec"
assert len(in_values) == len(out_values) == 1600, f"{len(in_values)} / {len(out_values)} samples"
mae = sum(abs(a - b) for a, b in zip(in_values, out_values)) / len(in_values)
assert mae < 20000, f"mean absolute error too large: {mae:.0f} of 8388608"
print(f"        [ok] lossy but faithful: mean absolute error {mae:.0f} (~{mae / 83886.08:.2f}% FS)")
PYEOF

# 5) aptX HD round trip.  4 samples (24 bytes) become 6 bytes here, so 800
#    frames = 200 blocks x 6 bytes, plus the same 92 frame (23 block) flush.
echo "[test] freeaptxenc --hd < in.raw > out.hd"
freeaptxenc --hd < "$TESTDIR/in.raw" > "$TESTDIR/out.hd"
HD_SIZE=$(wc -c < "$TESTDIR/out.hd")
[ "$HD_SIZE" -eq 1338 ] || { echo "unexpected aptX HD size: $HD_SIZE (want 1338)"; exit 1; }
echo "        [ok] $HD_SIZE bytes of aptX HD (1200 + 138 flush)"

echo "[test] freeaptxdec --hd < out.hd > dec.hd"
freeaptxdec --hd < "$TESTDIR/out.hd" > "$TESTDIR/dec.hd"
HD_DEC_SIZE=$(wc -c < "$TESTDIR/dec.hd")
[ "$HD_DEC_SIZE" -eq "$IN_SIZE" ] || {
    echo "aptX HD round trip changed the PCM size: $IN_SIZE -> $HD_DEC_SIZE"; exit 1
}
echo "        [ok] decoded back to $HD_DEC_SIZE bytes"

# 6) Negative controls: an unknown option and a stream that is not aptX data
#    must never be reported as success.
echo "[test] unknown options (expected failure)"
for bad in "--bogus" "-Z"; do
    if freeaptxenc "$bad" >/dev/null 2>&1; then
        echo "freeaptxenc accepted the unknown option $bad"; exit 1
    fi
    if freeaptxdec "$bad" >/dev/null 2>&1; then
        echo "freeaptxdec accepted the unknown option $bad"; exit 1
    fi
done
echo "        [ok] unknown options rejected"

echo "[test] non-aptX stream (expected failure)"
printf 'this is definitely not an aptX stream' > "$TESTDIR/garbage.bin"
if freeaptxdec < "$TESTDIR/garbage.bin" >/dev/null 2>&1; then
    echo "freeaptxdec accepted a stream that is not aptX"; exit 1
fi
echo "        [ok] non-aptX stream rejected"

echo "All tests passed."