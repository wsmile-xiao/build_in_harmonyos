#!/bin/sh
# test_package/test.sh — functional smoke test for the fdk-aac-encoder package.
# Runs in conanrun env; exercised from test_package/conanfile.py.
#
# Real encode (R34): generate a 440 Hz stereo WAV, encode AAC-LC via the
# packaged fdkaac binary, then inspect both M4A and ADTS outputs.
set -eu

FDKAAC="${1:?usage: test.sh <path-to-fdkaac>}"
WORKDIR="${2:-.}"

echo "[test] fdkaac --help (version banner; upstream -h exits 1 by design)"
banner=$("$FDKAAC" --help 2>&1 || true)
echo "$banner" | head -1
case "$banner" in
    "fdkaac 1.0.9"*) echo "PASS: version banner OK" ;;
    *) echo "FAIL: unexpected banner: $(echo "$banner" | head -1)"; exit 1 ;;
esac

# Generate 0.5 s of 440 Hz stereo 16-bit PCM WAV (portable: printf + od-free).
python3 - "$WORKDIR/tone.wav" <<'PY'
import struct, sys, wave
with wave.open(sys.argv[1], "w") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(44100)
    frames = bytearray()
    for i in range(22050):
        v = int(12000.0 * __import__("math").sin(2 * 3.141592653589793 * 440 * i / 44100))
        frames += struct.pack("<hh", v, v)
    w.writeframes(bytes(frames))
PY

echo "[test] fdkaac AAC-LC 128 kbps encode (M4A)"
"$FDKAAC" -b 128000 --silent -o "$WORKDIR/tone.m4a" "$WORKDIR/tone.wav"
size=$(wc -c < "$WORKDIR/tone.m4a")
head_bytes=$(head -c 12 "$WORKDIR/tone.m4a" | od -An -c | tr -d ' \n')
case "$head_bytes" in
    *ftyp*M4A*) echo "PASS: M4A container valid ($size bytes)" ;;
    *) echo "FAIL: not an M4A container: $head_bytes"; exit 1 ;;
esac
[ "$size" -gt 1024 ] || { echo "FAIL: encoded file too small: $size"; exit 1; }

echo "[test] fdkaac raw-input ADTS encode"
"$FDKAAC" -b 128000 --silent -f 2 -o "$WORKDIR/tone.aac" \
    -R --raw-channels 1 --raw-rate 44100 "$WORKDIR/tone.wav"
sync=$(head -c 2 "$WORKDIR/tone.aac" | od -An -tx1 | tr -d ' \n')
case "$sync" in
    ff*f*) echo "PASS: ADTS sync word valid ($sync)" ;;
    *) echo "FAIL: not ADTS: $sync"; exit 1 ;;
esac

echo "PASS: fdk-aac-encoder test_package completed"
