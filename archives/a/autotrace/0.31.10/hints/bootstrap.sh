#!/bin/sh
# Bootstrap script for autotrace 0.31.10
# Since autoreconf fails due to configure.ac issues, we use pre-generated configure
# from the build work directory

set -e

# The pre-generated autotools files are stored in the build work directory
# This is a workaround for the case where original tarball lacks configure script
# and autoreconf fails due to configure.ac syntax issues
PREGEN_DIR="/storage/Users/currentUser/builds/autotrace-0.31.10.work"

if [ ! -d "$PREGEN_DIR" ]; then
    echo "[bootstrap] ERROR: Pre-generated files not found at $PREGEN_DIR"
    echo "[bootstrap] Please ensure the build work directory exists with configure files"
    exit 1
fi

echo "[bootstrap] Copying pre-generated autotools files from $PREGEN_DIR..."

# Copy essential autotools files
cp -f "$PREGEN_DIR/configure" ./configure || exit 1
cp -f "$PREGEN_DIR/Makefile.in" ./Makefile.in || exit 1
cp -f "$PREGEN_DIR/config.h.in" ./config.h.in || exit 1
cp -f "$PREGEN_DIR/config.guess" ./config.guess || exit 1
cp -f "$PREGEN_DIR/config.sub" ./config.sub || exit 1
cp -f "$PREGEN_DIR/aclocal.m4" ./aclocal.m4 || exit 1
cp -f "$PREGEN_DIR/ltmain.sh" ./ltmain.sh || exit 1
cp -f "$PREGEN_DIR/compile" ./compile || exit 1
cp -f "$PREGEN_DIR/missing" ./missing || exit 1
cp -f "$PREGEN_DIR/install-sh" ./install-sh || exit 1
cp -f "$PREGEN_DIR/ABOUT-NLS" ./ABOUT-NLS || exit 1
cp -f "$PREGEN_DIR/autotrace.pc" ./autotrace.pc || exit 1
cp -f "$PREGEN_DIR/config.rpath" ./config.rpath 2>/dev/null || true

# Copy m4 directory if it exists
if [ -d "$PREGEN_DIR/m4" ]; then
    mkdir -p m4
    cp -rf "$PREGEN_DIR/m4/"* ./m4/ 2>/dev/null || true
fi

# Copy po directory files (needed for gettext)
if [ -d "$PREGEN_DIR/po" ]; then
    mkdir -p po
    cp -f "$PREGEN_DIR/po/Makefile.in.in" ./po/Makefile.in.in 2>/dev/null || true
    cp -f "$PREGEN_DIR/po/Makefile.in" ./po/Makefile.in 2>/dev/null || true
fi

# Ensure executable permissions
chmod +x configure config.guess config.sub compile missing install-sh config.rpath

# Set LDFLAGS for configure (required to link libintl.a for glib static linking)
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib /storage/Users/currentUser/usr/local/lib/libintl.a"

echo "[bootstrap] Done. configure script ready."
echo "[bootstrap] LDFLAGS has been set to link libintl.a for glib."