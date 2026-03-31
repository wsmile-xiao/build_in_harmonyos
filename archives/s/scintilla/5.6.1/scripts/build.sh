#!/bin/sh
# Build Scintilla core library for HarmonyOS
set -e

SRC_DIR="${1:-.}"
BUILD_DIR="${2:-build_ohos}"
PREFIX="${3:-$HOME/usr/local}"

echo "Building Scintilla 5.6.1 for HarmonyOS..."
echo "Source: $SRC_DIR"
echo "Build:  $BUILD_DIR"
echo "Prefix: $PREFIX"

mkdir -p "$BUILD_DIR"

# Compile all core source files
for f in "$SRC_DIR"/src/*.cxx; do
    name=$(basename "$f" .cxx)
    echo "  Compiling $name..."
    clang++ -std=c++17 -fPIC -O2 -DNDEBUG \
        -I "$SRC_DIR/include" -I "$SRC_DIR/src" \
        -c "$f" -o "$BUILD_DIR/${name}.o"
done

# Compile platform stubs
echo "  Compiling PlatOHOS..."
clang++ -std=c++17 -fPIC -O2 -DNDEBUG \
    -I "$SRC_DIR/include" -I "$SRC_DIR/src" \
    -c "$SRC_DIR/ohos/PlatOHOS.cxx" -o "$BUILD_DIR/PlatOHOS.o"

# Create static library
echo "Creating static library..."
cd "$BUILD_DIR"
llvm-ar rcs libscintilla_core.a *.o
llvm-ranlib libscintilla_core.a

# Install
echo "Installing to $PREFIX..."
mkdir -p "$PREFIX/lib"
mkdir -p "$PREFIX/include/scintilla"
mkdir -p "$PREFIX/include/scintilla/internal"
cp libscintilla_core.a "$PREFIX/lib/"
cp "$SRC_DIR"/include/*.h "$PREFIX/include/scintilla/"
cp "$SRC_DIR"/src/*.h "$PREFIX/include/scintilla/internal/"

echo ""
echo "=== Build complete ==="
echo "Library: $PREFIX/lib/libscintilla_core.a"
echo "Headers: $PREFIX/include/scintilla/"
ls -lh "$PREFIX/lib/libscintilla_core.a"
