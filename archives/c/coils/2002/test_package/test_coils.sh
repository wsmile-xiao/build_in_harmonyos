#!/bin/sh
# Exercise the packaged predictor using the upstream README sample input.
set -eu

: "${COILSDIR:?COILSDIR must point to the packaged matrix data}"

output="1srya-coils.fasta"
ncoils -f < "1srya.fa" > "$output"
grep -q '^>1srya ' "$output"
grep -q 'xxxxxxxx' "$output"

echo "coils functional test passed"
