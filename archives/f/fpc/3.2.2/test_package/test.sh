#!/usr/bin/env bash
# L1 consumer test for fpc/3.2.2 (application package).
#
# Runs the packaged, relocatable `fpc` launcher against a small upstream-style
# Pascal program: it must report its version/target, compile the program with
# the packaged RTL and then execute the produced static binary.
set -euo pipefail

fpc="$1"
here="$(cd -P "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cp "$here/hello.pas" "$tmp/hello.pas"

echo "fpc -iV     : $("$fpc" -iV)"
echo "fpc -iTP -iTO: $("$fpc" -iTP -iTO)"

cd "$tmp"
"$fpc" hello.pas
./hello
