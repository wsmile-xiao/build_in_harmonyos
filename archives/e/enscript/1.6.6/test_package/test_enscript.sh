#!/bin/bash
# test_enscript.sh — verify the enscript binary converts text to PostScript.
# Called by test_package/conanfile.py test() method with the binary path as $1.
# Deliberately avoids `set -e`/pipefail so every step reports its own status.

ENSCRIPT_BIN="$1"
echo "[test] binary: $ENSCRIPT_BIN"

if [ -z "${ENSCRIPT_BIN:-}" ] || [ ! -x "$ENSCRIPT_BIN" ]; then
    echo "FAIL: enscript binary not found or not executable"
    exit 1
fi

# enscript hardcodes its data/config dir at compile time; after relocation it
# needs ENSCRIPT_LIBRARY to find the bundled fonts and (via ../../etc)
# enscript.cfg. Derive it from the binary path so the test does not depend on
# the runenv being active. OHOS /tmp is read-only (E002), so keep temp files
# in a writable dir via TMPDIR.
pkg_dir=$(cd "$(dirname "$ENSCRIPT_BIN")/.." && pwd)
export ENSCRIPT_LIBRARY="${ENSCRIPT_LIBRARY:-$pkg_dir/share/enscript}"
work="$(pwd)/enscript-test-work"
rm -rf "$work"; mkdir -p "$work"
export TMPDIR="$work"
echo "[test] ENSCRIPT_LIBRARY=$ENSCRIPT_LIBRARY TMPDIR=$TMPDIR"

# 1) --version smoke check
verout=$("$ENSCRIPT_BIN" --version 2>&1); vrc=$?
echo "[test] --version exit=$vrc: $(echo "$verout" | sed -n 1p)"
if [ $vrc -ne 0 ] || ! echo "$verout" | grep -qi "enscript"; then
    echo "FAIL: --version failed"; echo "$verout"; exit 1
fi
echo "PASS: --version"

# 2) Core function: convert a text file to PostScript.
in="$work/sample.txt"
out="$work/sample.ps"
printf 'Hello, HarmonyOS PC!\nenscript text-to-PostScript conversion.\n' > "$in"

"$ENSCRIPT_BIN" -B -p "$out" "$in" 2>"$work/err.log"; crc=$?
echo "[test] convert exit=$crc"
[ $crc -eq 0 ] || { echo "FAIL: conversion returned $crc"; cat "$work/err.log"; exit 1; }
[ -s "$out" ] || { echo "FAIL: output PostScript is empty"; cat "$work/err.log"; exit 1; }
firstline=$(sed -n 1p "$out")
case "$firstline" in
    %!PS*) echo "PASS: generated valid PostScript ($(wc -c < "$out") bytes)";;
    *) echo "FAIL: output is not PostScript (first line: $firstline)"; exit 1;;
esac

rm -rf "$work"
echo "[test] OK"
