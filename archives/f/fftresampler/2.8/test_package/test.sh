#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer verification for the FFTResampler CLI.
# Runs in the conanrun env (PATH includes the installed bin/ directory).
# Generates a small PCM WAV input, resamples it 44100 -> 8000 Hz, and verifies
# the output file is a valid RIFF/WAVE with the expected sample rate.
set -eu

echo "[test] fftresampler 2.8 consumer verification"

TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT

IN="$TMPD/in.wav"
OUT="$TMPD/out.wav"

# ---- build a minimal mono 16-bit PCM WAV (0.05 s @ 44100 Hz) via printf ----
le16() { printf "\\x$(printf '%02x' $(( $1 & 255 )))\\x$(printf '%02x' $(( ($1 >> 8) & 255 )))"; }
le32() {
  printf "\\x$(printf '%02x' $(( $1 & 255 )))\\x$(printf '%02x' $(( ($1 >> 8) & 255 )))\\x$(printf '%02x' $(( ($1 >> 16) & 255 )))\\x$(printf '%02x' $(( ($1 >> 24) & 255 )))"
}

RATE=44100
SAMPLES=$(( RATE / 20 ))          # 0.05 s
DATASIZE=$(( SAMPLES * 2 ))
RIFFSIZE=$(( 36 + DATASIZE ))

{
  printf 'RIFF'; le32 "$RIFFSIZE"; printf 'WAVE'
  printf 'fmt '; le32 16; le16 1; le16 1; le32 "$RATE"; le32 $(( RATE * 2 )); le16 2; le16 16
  printf 'data'; le32 "$DATASIZE"
  # 0.05 s of a 440 Hz sine, 16-bit PCM
  python3 - "$SAMPLES" <<'PYEOF'
import math, struct, sys
n = int(sys.argv[1])
data = b''.join(struct.pack('<h', int(12000 * math.sin(2 * math.pi * 440 * i / 44100))) for i in range(n))
sys.stdout.buffer.write(data)
PYEOF
} > "$IN"

echo "[test] input wav: $IN ($(wc -c < "$IN") bytes)"

# ---- run the installed binary: input output target_rate ----
FFTResampler "$IN" "$OUT" 8000
rc=$?
[ "$rc" = "0" ] || { echo "FAIL: FFTResampler exit=$rc"; exit 1; }
echo "PASS 1: FFTResampler exit=$rc"

[ -f "$OUT" ] || { echo "FAIL: output wav missing"; exit 1; }
OUTSIZE=$(wc -c < "$OUT")
[ "$OUTSIZE" -gt 44 ] || { echo "FAIL: output wav too small ($OUTSIZE)"; exit 1; }
echo "PASS 2: output wav exists ($OUTSIZE bytes)"

# ---- verify output header: RIFF/WAVE + fmt rate == 8000 ----
MAGIC=$(head -c 4 "$OUT")
[ "$MAGIC" = "RIFF" ] || { echo "FAIL: bad magic [$MAGIC]"; exit 1; }
python3 - "$OUT" <<'PYEOF'
import struct, sys
d = open(sys.argv[1], 'rb').read()
assert d[8:12] == b'WAVE'
pos = 12
rate = None
while pos + 8 <= len(d):
    cid = d[pos:pos+4]; csize = struct.unpack('<I', d[pos+4:pos+8])[0]
    if cid == b'fmt ' and csize >= 16:
        afmt, ch, r = struct.unpack('<HHI', d[pos+8:pos+16])
        assert afmt == 3, f"expected IEEE float (3), got {afmt}"
        assert ch == 1, f"expected mono, got {ch}"
        rate = r
        break
    pos += 8 + csize + (csize & 1)
assert rate == 8000, f"expected rate 8000, got {rate}"
print(f"PASS 3: output wav fmt=IEEE-float mono rate={rate}")
PYEOF

echo "test fftresampler 2.8: 3/3 checks PASS"
exit 0