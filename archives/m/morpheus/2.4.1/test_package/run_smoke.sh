#!/bin/sh
set -eu

morpheus="$1"
smoke="$2"
out="${3:-morpheus-smoke.out}"

"$morpheus" --file "$smoke" > "$out" 2>&1
grep -q "Simulation finished" "$out"
