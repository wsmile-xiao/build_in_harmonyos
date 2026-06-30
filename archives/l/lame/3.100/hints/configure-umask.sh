#!/bin/sh
# Fix E011: HMDFS filesystem umask 077 permission issue
# HMDFS UID mapping causes tmpdir created with umask 077 to be unwritable
# This script patches configure to use umask 022 instead of umask 077

if [ -f configure ]; then
    sed -i 's/umask 077/umask 022/g' configure
    echo "Patched configure: umask 077 → umask 022 (E011 fix)"
fi

# Also patch config.status if it exists
if [ -f config.status ]; then
    sed -i 's/umask 077/umask 022/g' config.status
    echo "Patched config.status: umask 077 → umask 022 (E011 fix)"
fi