#!/bin/sh
# test_package smoke for cdemud (L2-class, R34: real execution, no stub).
#
# Usage: sh test.sh <path-to-packaged-cdemud>
# Runs the packaged daemon binary with --help (GOption built-in) and
# requires the usage header in the output. cdemud 1.0.0 parses options
# before any daemon initialization, so no D-Bus bus or vhba device is
# needed for this path.
set -e

BIN="$1"
[ -n "$BIN" ] || { echo "usage: $0 <cdemud binary>" >&2; exit 2; }
[ -x "$BIN" ] || { echo "FAIL: $BIN is not executable" >&2; exit 1; }

HELP_OUT=$("$BIN" --help 2>&1) || { echo "FAIL: --help exited non-zero" >&2; exit 1; }
echo "$HELP_OUT" | grep -q "Usage:" || { echo "FAIL: no Usage header in --help output" >&2; exit 1; }
echo "$HELP_OUT" | grep -q "CDEmu" || { echo "FAIL: no CDEmu banner in --help output" >&2; exit 1; }

echo "cdemud test_package: --help smoke passed"
