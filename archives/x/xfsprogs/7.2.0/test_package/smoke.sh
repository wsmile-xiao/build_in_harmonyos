#!/bin/sh
# Executed by test_package/conanfile.py test() — version probes for the
# packaged xfsprogs tools.  All operations are safe (no device access).
set -e
SBIN="$1"

"$SBIN/mkfs.xfs" -V
"$SBIN/xfs_db" -V
"$SBIN/xfs_repair" -V
"$SBIN/xfs_io" -V
"$SBIN/xfs_spaceman" -V
