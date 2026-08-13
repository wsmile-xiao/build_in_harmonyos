#!/bin/sh
set -eu

PKG="$1"

LUA="$PKG/usr/share/lua/5.4/aconf/modules/dnsmasq.lua"
AUG="$PKG/usr/share/aconf/augeas/aconf_dnsmasq.aug"

if [ ! -f "$LUA" ]; then
    echo "FAIL: dnsmasq.lua not found: $LUA"
    exit 1
fi

echo "PASS: dnsmasq.lua exists"

if ! grep -F "aconf.model" "$LUA" >/dev/null; then
    echo "FAIL: aconf.model dependency not found"
    exit 1
fi

echo "PASS: aconf.model dependency found"

if [ ! -f "$AUG" ]; then
    echo "FAIL: Augeas file not found: $AUG"
    exit 1
fi

echo "PASS: aconf_dnsmasq.aug exists"

echo "PASS: aconf-mod-dnsmasq smoke test completed"
