#!/bin/sh
# Fix config.status tmpdir issue for HarmonyOS
# The $ac_tmp variable is empty due to shell limitations, causing config.status to fail

# Get the absolute path of the source directory
SRC_DIR=$(pwd)

# Set TMPDIR to a fixed directory
export TMPDIR=${TMPDIR:-/storage/Users/currentUser/tmp}
export PKG_CONFIG_PATH=${PKG_CONFIG_PATH:-/storage/Users/currentUser/usr/local/lib/pkgconfig}

# Run configure first to generate config.status
./configure --prefix=/storage/Users/currentUser/usr/local

# If configure fails due to tmpdir, fix config.status and rerun
if [ $? -ne 0 ] && [ -f config.status ]; then
    FIXED_TMP="$SRC_DIR/tmp/config-tmp"
    mkdir -p "$FIXED_TMP"

    # Replace $ac_tmp with fixed directory
    sed -i 's|\$ac_tmp|'"$FIXED_TMP"'|g' config.status

    # Rerun config.status
    ./config.status
fi

# Verify Makefile was created
if [ -f Makefile ]; then
    echo "configure completed successfully"
    exit 0
else
    echo "configure failed - Makefile not created"
    exit 1
fi