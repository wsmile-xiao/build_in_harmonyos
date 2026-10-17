#!/bin/sh
# test_picat.sh — L0c smoke test wrapper for picat
# Runs picat with test_picat.pi to verify the binary works
set -eu

PICAT_BIN="${1:-picat}"
PICATPATH="${2:-.}"

"$PICAT_BIN" "$PICATPATH/test_picat.pi"
