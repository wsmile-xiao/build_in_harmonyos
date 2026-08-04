#!/bin/sh
set -eu
set -o pipefail

BIN_DIR="$1"
WORK_DIR="${TMPDIR:-/data/local/tmp}/jpeg-archive-test-$$"
mkdir -p "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT HUP INT TERM

JPEG_RECOMPRESS="$BIN_DIR/jpeg-recompress"
JPEG_COMPARE="$BIN_DIR/jpeg-compare"
JPEG_HASH="$BIN_DIR/jpeg-hash"
JPEG_ARCHIVE="$BIN_DIR/jpeg-archive"

for command in "$JPEG_RECOMPRESS" "$JPEG_COMPARE" "$JPEG_HASH" "$JPEG_ARCHIVE"; do
    test -x "$command"
done

# Build a 64x64 P6 (binary) PPM filled with deterministic noise.
# jpeg-archive's checkPpmMagic only accepts P6, not P3 (ASCII).
# A 64x64 image is large enough that jpeg-recompress encodes a real
# JPEG instead of falling back to the copy-files branch.
# Pixel payload = 64*64*3 = 12288 bytes, pulled from /dev/urandom so
# the image has real entropy for the SSIM/MS-SSIM comparators.
printf 'P6\n64 64\n255\n' > "$WORK_DIR/input.ppm"
head -c 12288 /dev/urandom >> "$WORK_DIR/input.ppm"

"$JPEG_RECOMPRESS" --ppm "$WORK_DIR/input.ppm" "$WORK_DIR/output.jpg" >/dev/null 2>&1
test -s "$WORK_DIR/output.jpg"

"$JPEG_COMPARE" "$WORK_DIR/output.jpg" "$WORK_DIR/output.jpg" >/dev/null 2>&1

HASH1=$("$JPEG_HASH" "$WORK_DIR/output.jpg")
HASH2=$("$JPEG_HASH" "$WORK_DIR/output.jpg")
test -n "$HASH1"
test "$HASH1" = "$HASH2"

echo "jpeg-archive functional smoke tests passed"
