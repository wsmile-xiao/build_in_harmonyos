#!/bin/sh
set -eu

PKG="$1"
FILE="$PKG/usr/share/lua/5.4/aconf/modules/strongswan.lua"

if [ ! -f "$FILE" ]; then
    echo "FAIL: strongswan.lua not found: $FILE"
    exit 1
fi

echo "PASS: strongswan.lua exists"

if ! grep -F "require('aconf.model')" "$FILE" >/dev/null; then
    echo "FAIL: acf.model dependency not found"
    exit 1
fi

echo "PASS: acf.model dependency found"

if ! grep -F "require('aconf.util')" "$FILE" >/dev/null; then
    echo "FAIL: acf.util dependency not found"
    exit 1
fi

echo "PASS: acf.util dependency found"

echo "PASS: aconf-mod-strongswan smoke test completed"
