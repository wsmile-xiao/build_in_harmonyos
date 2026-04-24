#!/bin/sh
# Fix config.status tmpdir issue for toybox sh
# toybox sh doesn't pass variables to subprocesses, causing $ac_tmp to be empty
# This script patches config.status to use a fixed tmpdir

TMPDIR=${TMPDIR:-/storage/Users/currentUser/tmp}
FIXED_TMP="$TMPDIR/speexdsp-config-tmp"

# Ensure fixed tmpdir exists
mkdir -p "$FIXED_TMP"

# Patch config.status to use fixed tmpdir instead of $ac_tmp
if [ -f config.status ]; then
    sed -i 's|$ac_tmp|/storage/Users/currentUser/tmp/speexdsp-config-tmp|g' config.status
    echo "Patched config.status to use fixed tmpdir: $FIXED_TMP"
fi
