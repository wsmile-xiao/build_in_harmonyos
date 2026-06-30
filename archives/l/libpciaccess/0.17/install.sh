#!/bin/sh
# libpciaccess 0.17 install script for HarmonyOS/OpenHarmony (aarch64)
# This script installs the PCI device access library

PREFIX="${PREFIX:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing libpciaccess 0.17 to $PREFIX..."

# Create directories
mkdir -p "$PREFIX/bin"
mkdir -p "$PREFIX/lib"
mkdir -p "$PREFIX/include"
mkdir -p "$PREFIX/lib/pkgconfig"

# Copy files
cp -a "$SCRIPT_DIR/usr/local/bin/scanpci" "$PREFIX/bin/"
cp -a "$SCRIPT_DIR/usr/local/lib/libpciaccess.so*" "$PREFIX/lib/"
cp -a "$SCRIPT_DIR/usr/local/include/pciaccess.h" "$PREFIX/include/"
cp -a "$SCRIPT_DIR/usr/local/lib/pkgconfig/pciaccess.pc" "$PREFIX/lib/pkgconfig/"

# Update pkgconfig path
sed -i "s|/storage/Users/currentUser/usr/local|$PREFIX|g" "$PREFIX/lib/pkgconfig/pciaccess.pc"

echo "Installation complete!"
echo "Library installed to: $PREFIX/lib/libpciaccess.so.0.11.1"
echo "Header installed to: $PREFIX/include/pciaccess.h"
echo "Tool installed to: $PREFIX/bin/scanpci"

# Verify installation
if [ -f "$PREFIX/lib/libpciaccess.so.0.11.1" ]; then
    echo "SUCCESS: libpciaccess 0.17 installed"
else
    echo "FAILED: Installation error"
    exit 1
fi