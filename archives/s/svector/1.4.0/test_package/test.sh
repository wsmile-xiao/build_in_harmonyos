#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the svector header-only library.
# Compiles test_svector.cpp against the packaged header, signs the resulting
# executable (OHOS only loads ELF files carrying a valid .codesign section,
# see knowledge E077) and runs it. Requires $1 = packaged include dir.
set -euo pipefail

INC="$1"
CXX=${CXX:-clang++}
CXXFLAGS=${CXXFLAGS:-}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

echo "[test] compiling consumer against installed header"
"$CXX" $CXXFLAGS -std=c++17 -I"$INC" \
    "$(dirname "$0")/test_svector.cpp" -o "$OUT/test_svector"

echo "[test] signing test executable (E077)"
SIGNER=$(command -v binary-sign-tool || echo /data/service/hnp/bin/binary-sign-tool)
OBJCOPY=$(command -v llvm-objcopy || echo /data/service/hnp/bin/llvm-objcopy)
# the freshly linked binary may not carry the placeholder section — absence is fine
LD_LIBRARY_PATH= "$OBJCOPY" --remove-section .codesign "$OUT/test_svector" 2>/dev/null || true
LD_LIBRARY_PATH= "$SIGNER" sign -inFile "$OUT/test_svector" \
    -outFile "$OUT/test_svector.signed" -selfSign 1
chmod 755 "$OUT/test_svector.signed"

echo "[test] running consumer assertions"
"$OUT/test_svector.signed"
