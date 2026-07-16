#!/data/service/hnp/bin/bash
# test_package/test.sh — L1 consumer test for unpaper 7.0.0.
#
# Invoked by conanfile.py's test() under the conanrun env, where PATH includes
# the installed bin/ — so `unpaper` resolves by name. R34: the test genuinely
# exercises the unpaper binary's image I/O (libavformat/libavcodec path):
#   1) `unpaper --version` — arg parsing + av library initialisation
#   2) an 8x8 PPM round-trip — real decode/process/encode of an image
set -euo pipefail

echo "[step] unpaper --version"
unpaper --version

echo "[step] PPM image round-trip"
# Synthesize a valid 8x8 RGB PPM (P6): 11-byte header + 192 bytes pixel data.
{ printf 'P6\n8 8\n255\n'; head -c 192 /dev/zero; } > in.ppm
unpaper --layout none in.ppm out.ppm

# Assert a non-empty output image was produced.
test -s out.ppm
echo "        [ok] out.ppm produced ($(wc -c < out.ppm) bytes)"
echo "PASS: unpaper smoke test"
