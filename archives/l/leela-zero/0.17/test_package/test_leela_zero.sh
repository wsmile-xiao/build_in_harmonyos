#!/bin/sh
set -eu

exe="$1"
out="leelaz-help.txt"

"$exe" --help > "$out"

grep -q "Generic options" "$out"
grep -q -- "--gtp" "$out"

echo "leela-zero help-output smoke test passed"
