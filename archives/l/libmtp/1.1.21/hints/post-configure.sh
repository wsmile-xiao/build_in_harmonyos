#!/bin/sh
# Fix config.status tmpdir issue for HMDFS SELinux restrictions
# In HarmonyOS, mktemp -d "./confXXXXXX" may fail due to SELinux permissions
# This script patches config.status to use a fixed tmpdir

TMPDIR=${TMPDIR:-/storage/Users/currentUser/tmp}
FIXED_TMP="$TMPDIR/libmtp-config-tmp"

# Ensure fixed tmpdir exists
mkdir -p "$FIXED_TMP"

# Patch config.status to use fixed tmpdir instead of $ac_tmp
if [ -f config.status ]; then
    # Method 1: Replace ac_tmp with fixed path
    sed -i "s|\$ac_tmp|$FIXED_TMP|g" config.status
    
    # Method 2: Also replace direct tmp variable references
    sed -i "s|tmp=\./conf\$\$-\$RANDOM|tmp=$FIXED_TMP|g" config.status
    
    # Ensure the directory has correct permissions
    chmod 777 "$FIXED_TMP" 2>/dev/null || true
    
    echo "Patched config.status to use fixed tmpdir: $FIXED_TMP"
fi
