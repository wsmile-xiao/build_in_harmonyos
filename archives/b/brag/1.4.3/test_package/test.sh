#!/bin/sh
set -eu

echo "=== Test 1: packaged commands are available ==="
command -v brag >/dev/null
command -v tclsh8.6 >/dev/null
command -v uudeview >/dev/null

echo "PASS: brag, tclsh8.6 and uudeview are available"

echo "=== Test 2: Tcl runtime works ==="
TCL_VERSION="$(printf 'puts [info patchlevel]\n' | tclsh8.6)"
test "$TCL_VERSION" = "8.6.14"
echo "PASS: Tcl $TCL_VERSION"

echo "=== Test 3: uudeview runtime works ==="
set +e
UU_OUTPUT="$(uudeview --help 2>&1)"
UU_RC=$?
set -e

test "$UU_RC" -eq 99
printf '%s\n' "$UU_OUTPUT" | grep -F "UUDEVIEW 0.5pl20" >/dev/null
printf '%s\n' "$UU_OUTPUT" | grep -F "uudeview [options] [file ...]" >/dev/null

echo "PASS: uudeview executable works and produced expected usage output"

echo "=== Test 4: brag usage path ==="
set +e
OUTPUT="$(brag --help 2>&1)"
RC=$?
set -e

test "$RC" -eq 1
printf '%s\n' "$OUTPUT" | grep -F "Usage: brag" >/dev/null
printf '%s\n' "$OUTPUT" | grep -F "Grab multipart binaries from news server" >/dev/null

echo "PASS: brag parsed by Tcl and produced expected usage output"
echo "=== All brag test_package checks passed ==="
