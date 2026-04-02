#!/bin/bash
# build_ohos.sh - Build libscintilla_ohos.so for HarmonyOS (aarch64)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCI_ROOT="$SCRIPT_DIR"
OHOS_DIR="$SCI_ROOT/ohos"
SRC_DIR="$SCI_ROOT/src"

# Toolchain
CLANG="/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++"
SYSROOT="/data/service/hnp/ohos-sdk.org/ohos-sdk_6.1.0.27/ohos/native/sysroot"

# Output
OUT_DIR="$SCRIPT_DIR/out"
OUT_SO="$OUT_DIR/libscintilla_ohos.so"

mkdir -p "$OUT_DIR"

echo "=== Building libscintilla_ohos.so ==="
echo "  Compiler: $CLANG"
echo "  Sysroot: $SYSROOT"

# Collect Scintilla core source files
CORE_SRC=$(find "$SRC_DIR" -name '*.cxx' | sort)
echo "  Core sources: $(echo "$CORE_SRC" | wc -l) files"

# Platform + OHOS source
OHOS_SRC="$OHOS_DIR/PlatOHOS.cxx $OHOS_DIR/ScintillaOHOS.cxx"

ALL_SRC="$CORE_SRC $OHOS_SRC"

# Common flags
CXXFLAGS="-std=c++17 -fPIC -O2 \
  -DSCI_OHOS \
  -DNDEBUG \
  -I$SCI_ROOT/include \
  -I$SRC_DIR \
  -I$OHOS_DIR \
  -I$SYSROOT/usr/include \
  -I$SYSROOT/usr/include/hilog \
  --sysroot=$SYSROOT"

LDFLAGS="-shared -Wl,-soname,libscintilla_ohos.so \
  -L$SYSROOT/usr/lib/aarch64-linux-ohos \
  -lnative_drawing \
  -lhilog_ndk.z"

echo "=== Compiling..."
$CLANG $CXXFLAGS $ALL_SRC $LDFLAGS -o "$OUT_SO"

echo "=== Build successful ==="
echo "  Output: $OUT_SO"
ls -lh "$OUT_SO"
