#!/usr/bin/zsh
# test_bpm.sh — Functional test for bpm-tools
# Generates synthetic 120 BPM audio and verifies bpm detects it correctly.
# Called by test_package/conanfile.py via self.run()

set -euo pipefail

TEST_TMPDIR="${TMPDIR:-/tmp}"
AUDIO_FILE="$TEST_TMPDIR/test_audio_120bpm.bin"
OUTPUT_FILE="$TEST_TMPDIR/bpm_output.txt"

# Generate 5 seconds of synthetic 120 BPM audio (44100Hz, mono, 32-bit float)
python3 -c "
import struct, sys
RATE=44100; DUR=5; BPM=120; bps=BPM/60.0
for i in range(int(RATE*DUR)):
    t=i/RATE; p=(t*bps)%1.0
    if p<0.03: v=0.9*(1-p/0.03)
    elif p<0.1: v=0.3*(1-(p-0.03)/0.07)
    else: v=0.01
    sys.stdout.buffer.write(struct.pack('f', v))
" > "$AUDIO_FILE"

# Run bpm with the synthetic audio
cat "$AUDIO_FILE" | bpm -m 60 -x 200 > "$OUTPUT_FILE"

# Read the detected BPM
DETECTED=$(cat "$OUTPUT_FILE")
echo "Detected BPM: $DETECTED (expected ~120)"

# Verify the result is within 5 BPM of 120
python3 -c "
detected = float('$DETECTED')
assert abs(detected - 120.0) < 5.0, f'BPM detection failed: got {detected}, expected ~120'
print('PASS: BPM detection within tolerance')
"

# Cleanup
rm -f "$AUDIO_FILE" "$OUTPUT_FILE"
