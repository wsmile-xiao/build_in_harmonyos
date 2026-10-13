#!/usr/bin/env bash
# L1 consumer test for lazarus/4.8.
#
# Usage: test.sh <lazbuild> <package_folder>
# HarmonyOS PC has no X server, so the GUI cannot be exercised; this asserts
# the headless CLI contract and the installed LCL/tools tree instead.
set -euo pipefail

lazbuild="$1"
pkg="$2"
lazarusdir="$pkg/share/lazarus"

[ -x "$lazbuild" ] || { echo "FAIL: lazbuild not executable: $lazbuild"; exit 1; }

echo "== lazbuild --version =="
version="$("$lazbuild" --version)"
echo "version: $version"
[ "$version" = "4.8" ] || { echo "FAIL: unexpected version: $version"; exit 1; }

echo "== lazbuild -v =="
[ "$("$lazbuild" -v)" = "4.8" ] || { echo "FAIL: -v mismatch"; exit 1; }

echo "== lazbuild --help =="
"$lazbuild" --help > /dev/null

echo "== installed LCL units (nogui) =="
for u in lcl.ppu interfaces.ppu; do
  found="$(find "$lazarusdir/lcl/units" -name "$u" -print -quit 2>/dev/null)"
  [ -n "$found" ] || { echo "FAIL: missing LCL unit $u"; exit 1; }
  echo "  $u: $found"
done

echo "== installed tools =="
for t in lazres updatepofiles lrstolfm; do
  [ -f "$lazarusdir/tools/$t" ] || { echo "FAIL: missing tool $t"; exit 1; }
  echo "  $t: ok"
done

echo "lazarus test: PASS"
