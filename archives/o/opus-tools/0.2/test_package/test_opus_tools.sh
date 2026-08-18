#!/bin/sh
set -euo pipefail 2>/dev/null || set -eu
# Functional test for opus-tools executables
# Usage: test_opus_tools.sh <bin_dir>
if [ $# -lt 1 ] || [ -z "$1" ]; then
    echo "Usage: $0 <bin_dir>"
    exit 1
fi
BIN_DIR="$1"
OPUSENC="$BIN_DIR/opusenc"
OPUSDEC="$BIN_DIR/opusdec"
OPUSINFO="$BIN_DIR/opusinfo"

# Verify all executables exist
for bin in "$OPUSENC" "$OPUSDEC" "$OPUSINFO"; do
    if [ ! -f "$bin" ]; then
        echo "FAIL: missing executable $bin"
        exit 1
    fi
done

# Create a simple WAV file with 1 second of silence (48000 Hz, 16-bit, mono)
WAV_FILE="silence.wav"
{
    # RIFF header
    printf 'RIFF'
    printf '\x24\x00\x00\x00'  # file size - 8 = 36
    printf 'WAVE'
    # fmt chunk
    printf 'fmt '
    printf '\x10\x00\x00\x00'  # chunk size = 16
    printf '\x01\x00'           # audio format = 1 (PCM)
    printf '\x01\x00'           # num channels = 1
    printf '\x80\xbb\x00\x00'  # sample rate = 48000
    printf '\x00\x77\x01\x00'  # byte rate = 96000
    printf '\x02\x00'           # block align = 2
    printf '\x10\x00'           # bits per sample = 16
    # data chunk
    printf 'data'
    printf '\x00\x00\x01\x00'  # data size = 65536
    # 32768 samples of silence (2 bytes each = 65536 bytes)
    dd if=/dev/zero bs=2 count=32768 2>/dev/null
} > "$WAV_FILE"

if [ ! -s "$WAV_FILE" ]; then
    echo "FAIL: could not create WAV file"
    exit 1
fi

# Encode WAV to Opus
OPUS_FILE="output.opus"
"$OPUSENC" "$WAV_FILE" "$OPUS_FILE" 2>/dev/null
if [ $? -ne 0 ] || [ ! -s "$OPUS_FILE" ]; then
    echo "FAIL: opusenc failed"
    rm -f "$WAV_FILE"
    exit 1
fi

# Inspect the Opus file
"$OPUSINFO" "$OPUS_FILE" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "FAIL: opusinfo failed"
    rm -f "$WAV_FILE" "$OPUS_FILE"
    exit 1
fi

# Decode Opus to raw PCM
PCM_FILE="decoded.raw"
"$OPUSDEC" "$OPUS_FILE" "$PCM_FILE" 2>/dev/null
if [ $? -ne 0 ] || [ ! -s "$PCM_FILE" ]; then
    echo "FAIL: opusdec failed"
    rm -f "$WAV_FILE" "$OPUS_FILE"
    exit 1
fi

# Clean up
rm -f "$WAV_FILE" "$OPUS_FILE" "$PCM_FILE"

echo "PASS opus-tools functional test (encode, inspect, decode)"
