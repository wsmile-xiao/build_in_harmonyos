#!/bin/bash
# resolvconf test script — verifies installation and normalize-resolvconf logic.
# Replicates key assertions from upstream debian/test-normalization.

set -euo pipefail

echo "Testing resolvconf installation..."

RESOLVCONF_BIN="${RESOLVCONF_BIN:-}"
RESOLVCONF_LIB="${RESOLVCONF_LIB:-}"

# Assertion 1: resolvconf binary exists
if [ ! -f "$RESOLVCONF_BIN" ]; then
    echo "ERROR: resolvconf binary not found: $RESOLVCONF_BIN"
    exit 1
fi
echo "ok - resolvconf binary exists"

# Assertion 2: resolvconf --help prints usage
help_output="$("$RESOLVCONF_BIN" --help 2>&1 || true)"
if ! echo "$help_output" | grep -q "Usage: resolvconf"; then
    echo "ERROR: resolvconf --help did not output usage text"
    exit 1
fi
echo "ok - resolvconf --help prints usage"

# Assertion 3: normalize-resolvconf helper exists
NORMALIZE="$RESOLVCONF_LIB/normalize-resolvconf"
if [ ! -f "$NORMALIZE" ]; then
    echo "ERROR: normalize-resolvconf not found: $NORMALIZE"
    exit 1
fi
echo "ok - normalize-resolvconf exists"

# Assertion 4: normalize-resolvconf strips comments and whitespace
result="$(echo "  nameserver  127.0.0.1 # foo	" | sed -f "$NORMALIZE")"
if [ "$result" != "nameserver 127.0.0.1" ]; then
    echo "ERROR: normalize-resolvconf comment/whitespace strip failed: got '$result'"
    exit 1
fi
echo "ok - normalize-resolvconf strips comments and whitespace"

# Assertion 5: normalize-resolvconf removes leading zeroes from IPv4
result="$(echo "nameserver 127.000.000.1" | sed -f "$NORMALIZE")"
if [ "$result" != "nameserver 127.0.0.1" ]; then
    echo "ERROR: normalize-resolvconf IPv4 zero-strip failed: got '$result'"
    exit 1
fi
echo "ok - normalize-resolvconf removes leading zeroes from IPv4"

# Assertion 6: normalize-resolvconf collapses IPv6 zeroes
result="$(echo "nameserver 0:0:0:0:0:0:0:1" | sed -f "$NORMALIZE")"
if [ "$result" != "nameserver ::1" ]; then
    echo "ERROR: normalize-resolvconf IPv6 collapse failed: got '$result'"
    exit 1
fi
echo "ok - normalize-resolvconf collapses IPv6 zeroes (0:0:0:0:0:0:0:1 -> ::1)"

# Assertion 7: list-records helper exists
LIST_RECORDS="$RESOLVCONF_LIB/list-records"
if [ ! -f "$LIST_RECORDS" ]; then
    echo "ERROR: list-records not found: $LIST_RECORDS"
    exit 1
fi
echo "ok - list-records helper exists"

# Assertion 8: config files installed
ETC_DIR="$(dirname "$(dirname "$RESOLVCONF_LIB")")/share/resolvconf/etc"
if [ ! -d "$ETC_DIR" ]; then
    echo "ERROR: resolvconf etc directory not found: $ETC_DIR"
    exit 1
fi
echo "ok - config files installed"

echo "All tests passed."
exit 0
