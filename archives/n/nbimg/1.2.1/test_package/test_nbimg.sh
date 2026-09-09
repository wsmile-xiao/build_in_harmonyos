#!/usr/bin/env bash
# nbimg 1.2.1 — consumer smoke test (same checks as conanfile.py test()).
# Usage: bash test_nbimg.sh <absolute-path-to-package-bin-dir>
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ]; then
    echo "usage: bash test_nbimg.sh <package bin dir>" >&2
    exit 2
fi

NBIMG="$BIN_DIR/nbimg"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "--- generate synthetic 320x240 RGB565 NB (white pixels) ---"
python3 - "$TMP/test.nb" <<'PY'
import struct, sys
path = sys.argv[1]
# 320x240 RGB565 (QVGA) pixel data, 2 bytes/pixel -> 153600 bytes
pixels = struct.pack("<H", 0xFFFF) * (320 * 240)
with open(path, "wb") as f:
    f.write(pixels)
PY

echo "--- nbimg -F (NB -> BMP, QVGA autodetect) ---"
"$NBIMG" -F "$TMP/test.nb" | grep -q "Done"
test -s "$TMP/test.nb.bmp"
echo "check passed: output BMP present and non-empty"

echo "nbimg NB->BMP smoke test passed"