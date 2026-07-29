#!/usr/bin/env sh
set -eu

PKG="${1:-}"
if [ -z "$PKG" ]; then
    echo "ERROR: package path is required"
    exit 1
fi

BIN="$PKG/bin"

for tool in psbook psselect pstops epsffit psnup psresize; do
    if [ ! -x "$BIN/$tool" ]; then
        echo "ERROR: missing executable $tool"
        exit 1
    fi
done

if [ ! -f "$PKG/lib/psutils/md68_0.ps" ] || [ ! -f "$PKG/lib/psutils/md71_0.ps" ]; then
    echo "ERROR: missing psutils resource files"
    exit 1
fi

set +e
output=$("$BIN/psselect" -? 2>&1)
status=$?
set -e

if [ "$status" -eq 0 ]; then
    echo "ERROR: psselect -? should return usage failure"
    printf "%s\n" "$output"
    exit 1
fi

if ! printf "%s\n" "$output" | grep -qi "usage"; then
    echo "ERROR: psselect usage output missing"
    printf "%s\n" "$output"
    exit 1
fi

echo "PASS: psutils packaged command set and resources"
