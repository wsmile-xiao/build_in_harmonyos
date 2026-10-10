#!/bin/sh
# Runs the consumer example that was linked against the packaged rutabaga
# (rutabaga_gfx) library.  $1 = path to the consumer binary.
set -e
BIN="$1"
if [ ! -x "$BIN" ]; then
    echo "consumer binary not executable: $BIN" >&2
    exit 1
fi
"$BIN"
