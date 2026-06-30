#!/bin/bash
# HMDFS SELinux workaround: Avoid mktemp issues in current directory
# Set TMPDIR to a writable location outside HMDFS

export TMPDIR=${TMPDIR:-/storage/Users/currentUser/tmp}
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# Create TMPDIR if it doesn't exist
mkdir -p "$TMPDIR"

# Run the original configure with proper options
./configure --prefix=/storage/Users/currentUser/usr/local "$@"
