#!/bin/sh
set -eu

PKG="$1"
FILE="$PKG/usr/share/lua/5.4/aconf/modules/dns-zone.lua"

if [ ! -f "$FILE" ]; then
    echo "FAIL: dns-zone.lua not found: $FILE"
    exit 1
fi

echo "PASS: dns-zone.lua exists"

if ! grep -F "aconf.model" "$FILE" >/dev/null; then
    echo "FAIL: aconf.model dependency not found"
    exit 1
fi

echo "PASS: aconf.model dependency found"

echo "PASS: aconf-mod-dns-zone smoke test completed"
