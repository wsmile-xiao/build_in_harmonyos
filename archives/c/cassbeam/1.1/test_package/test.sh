#!/bin/sh
# test_package/test.sh — cassbeam 1.1 functional test (3 real assertions).
# Runs the packaged binary on the upstream VLA example input and checks
# the science outputs are produced and non-empty. Guards against the
# silent-pass trap (empty files compared against empty files).
set -eu

CASSBEAM="${CASSBEAM:-cassbeam}"
# Prefer HMBS-injected TMPDIR (readonly /tmp gate); $$ = PID-unique subdir.
WORKDIR="${TMPDIR:-${TMP:-${TEMP:-$HOME/tmp}}}/cassbeam-test-$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT INT TERM

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$SCRIPT_DIR/vla-1500MHz.in"
GEOM="$SCRIPT_DIR/vla_geom"
if [ ! -f "$INPUT" ]; then
  echo "test input missing: $INPUT" >&2
  exit 1
fi
if [ ! -f "$GEOM" ]; then
  echo "test geom missing: $GEOM (cassbeam needs geom=vla_geom alongside the .in)" >&2
  exit 1
fi
cp "$INPUT" "$WORKDIR/input.in"
cp "$GEOM" "$WORKDIR/vla_geom"
cd "$WORKDIR"

# Assertion 1: binary runs to completion on the upstream example.
"$CASSBEAM" input.in > run.log 2>&1
echo "--- cassbeam run.log (tail) ---"
tail -n 20 run.log
grep -q "has finished" run.log

# Assertion 2: aperture outputs are produced and non-empty.
test -s vla-1500MHz.illumamp.pgm
test -s vla-1500MHz.illumphase.pgm
test -s vla-1500MHz.illumblock.pgm

# Assertion 3: parameter + far-field outputs are produced and non-empty.
test -s vla-1500MHz.params
test -s vla-1500MHz.I.pgm

echo "cassbeam test_package: all 3 assertions passed"
