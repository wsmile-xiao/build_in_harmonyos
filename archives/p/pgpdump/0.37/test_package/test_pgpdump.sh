#!/bin/bash
# test_pgpdump.sh — verify pgpdump binary is runnable.

set -euo pipefail

PGPDUMP_BIN="$1"

if [ -z "$PGPDUMP_BIN" ]; then
    echo "ERROR: pgpdump binary path not provided"
    exit 1
fi

if [ ! -x "$PGPDUMP_BIN" ]; then
    echo "ERROR: $PGPDUMP_BIN not found or not executable"
    exit 1
fi

output=$("$PGPDUMP_BIN" -v 2>&1)
if echo "$output" | grep -q "pgpdump version"; then
    echo "PASS: $output" | head -1
else
    echo "FAIL: unexpected output: $output"
    exit 1
fi
