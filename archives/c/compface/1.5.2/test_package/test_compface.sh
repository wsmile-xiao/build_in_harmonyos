#!/bin/sh
# test_compface.sh — compface/uncompface X-Face roundtrip test.
# Called by test_package/conanfile.py test() method.
#
# Args (passed by conanfile.py):
#   $1  res dir — contains the fixed fixture test.dat (48 lines of
#       "0x%04X,0x%04X,0x%04X,", the raw input format documented in
#       compface(1)).
#
# Scratch output files are created in a temp dir (TMPDIR) and removed, so
# nothing leaks into the source tree. Only POSIX tools (compface, uncompface,
# cmp, grep, wc) are used, so the test runs on the OHOS target without extra
# deps.
set -eu

res_dir="${1:-}"
[ -n "${res_dir}" ] || { echo "FAIL: missing arg1 (res dir)"; exit 1; }
[ -f "${res_dir}/test.dat" ] || { echo "FAIL: fixture test.dat missing"; exit 1; }

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/compface_test_XXXXXX")" \
  || { echo "FAIL: cannot create work dir"; exit 1; }
trap 'rm -rf "$work_dir"' EXIT

# Test 1: compression — compface produces a printable X-Face file
# (lines of space + printable characters, per compface(1)).
compface "${res_dir}/test.dat" "${work_dir}/face.txt" \
  || { echo "FAIL: compface compression failed"; exit 1; }
[ -s "${work_dir}/face.txt" ] || { echo "FAIL: empty X-Face output"; exit 1; }
if grep -qE '[^ -~]' "${work_dir}/face.txt"; then
  echo "FAIL: X-Face output contains non-printable characters"; exit 1
fi
echo "PASS: compression produced printable X-Face output"

# Test 2: lossless inverse — uncompface restores the fixture byte-exactly.
uncompface "${work_dir}/face.txt" "${work_dir}/round.dat" \
  || { echo "FAIL: uncompface decompression failed"; exit 1; }
cmp -s "${res_dir}/test.dat" "${work_dir}/round.dat" \
  || { echo "FAIL: roundtrip content mismatch (not lossless)"; exit 1; }
echo "PASS: decompression is byte-identical to the original"

# Test 3: XBM export — uncompface -X renders a standard XBM bitmap
# (#define header + the full 48x48x1 = 288 hex bytes).
uncompface -X "${work_dir}/face.txt" "${work_dir}/face.xbm" \
  || { echo "FAIL: uncompface -X failed"; exit 1; }
grep -q "_width" "${work_dir}/face.xbm" && grep -q "_height" "${work_dir}/face.xbm" \
  || { echo "FAIL: XBM output missing #define header"; exit 1; }
hexbytes=$(grep -oE '0[xX][0-9a-fA-F]{2}' "${work_dir}/face.xbm" | wc -l)
[ "${hexbytes}" -ge 288 ] \
  || { echo "FAIL: XBM output has only ${hexbytes} hex bytes (need 288 for 48x48x1)"; exit 1; }
echo "PASS: XBM export contains the full 48x48 bitmap (288 bytes)"

# Test 4: deterministic recompression — compressing the restored data
# again yields the identical X-Face.
compface "${work_dir}/round.dat" "${work_dir}/face2.txt" \
  || { echo "FAIL: recompression failed"; exit 1; }
cmp -s "${work_dir}/face.txt" "${work_dir}/face2.txt" \
  || { echo "FAIL: recompression is not deterministic"; exit 1; }
echo "PASS: recompression is deterministic"

echo "compface consumer test: all 4 checks passed"
