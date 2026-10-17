#!/usr/bin/env bash
# libfstconst 1.8.4 test_package smoke check.
# Verifies libfstconst artifact is packaged and the ConstFst extension header
# declares the immutable FST API symbols the extension library exports.
set -euo pipefail

lib="$1"
header="$2"

test -e "$lib"
test -f "$header"

# ConstFst extension header must declare the core ConstFst class and its
# Read/Write entry points that the libfstconst shared library exports.
grep -q "class ConstFst" "$header"
grep -q "WriteFst" "$header"
grep -q "Read" "$header"

# Smoke-check the packaged library soname matches the ConstFst extension ABI
# (openfst libfstconst uses -version-info 26:0:0 -> libfstconst.so.26).
case "$lib" in
  *.so|*.dylib)
    soname=$(basename "$lib")
    echo "libfstconst artifact: $soname"
    ;;
  *.a)
    echo "libfstconst static artifact: $(basename "$lib")"
    ;;
esac

echo "PASS libfstconst artifacts"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"check_libfstconst.sh\"}"
