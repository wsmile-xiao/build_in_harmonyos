#!/data/service/hnp/bin/bash
# test.sh — verify xorg-macros.m4 exists in util-macros package
# R34: substantively verifies package contents
set -euo pipefail

PKG_ROOT="$1"
if [ -z "$PKG_ROOT" ]; then
    echo "ERROR: package root path required"
    exit 1
fi

M4_FILE="$PKG_ROOT/share/aclocal/xorg-macros.m4"
PC_FILE="$PKG_ROOT/share/pkgconfig/xorg-macros.pc"

if [ ! -f "$M4_FILE" ]; then
    echo "ERROR: xorg-macros.m4 not found at $M4_FILE"
    exit 1
fi
echo "✅ xorg-macros.m4 found ($(wc -c < "$M4_FILE") bytes)"

if [ ! -f "$PC_FILE" ]; then
    echo "ERROR: util-macros.pc not found at $PC_FILE"
    exit 1
fi
echo "✅ util-macros.pc found"

# Verify M4 file contains XORG macro definitions
if ! grep -q "XORG_MACROS_VERSION\|XORG_PROG_RAWPROC" "$M4_FILE"; then
    echo "ERROR: xorg-macros.m4 does not contain expected XORG macros"
    exit 1
fi
echo "✅ xorg-macros.m4 contains XORG macro definitions"
