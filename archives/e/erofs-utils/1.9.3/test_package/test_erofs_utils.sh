#!/usr/bin/env bash
set -euo pipefail

package_folder="$1"

for utility in mkfs.erofs fsck.erofs dump.erofs mount.erofs; do
    executable=""
    for bindir in bin sbin; do
        candidate="$package_folder/$bindir/$utility"
        if test -x "$candidate"; then
            executable="$candidate"
            break
        fi
    done
    test -n "$executable"
    "$executable" --help >/dev/null
done
