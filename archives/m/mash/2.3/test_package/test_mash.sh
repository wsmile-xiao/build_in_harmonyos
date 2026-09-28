#!/bin/sh
set -eu

mash=$1
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT

"$mash" --version > "$scratch/version.txt"
grep -q '2.3' "$scratch/version.txt"

awk 'BEGIN { srand(7); print ">sample"; for (i=0; i<1200; i++) printf "%s", substr("ACGT", 1+int(rand()*4), 1); print "" }' > "$scratch/sample.fa"
"$mash" sketch -k 16 -s 100 -o "$scratch/sample" "$scratch/sample.fa"
test -s "$scratch/sample.msh"
"$mash" info "$scratch/sample.msh" > "$scratch/info.txt"
grep -q 'sample' "$scratch/info.txt"
"$mash" dist "$scratch/sample.msh" "$scratch/sample.msh" > "$scratch/dist.txt"
awk 'NF == 5 && $3 == 0 && $4 == 0 { good=1 } END { exit !good }' "$scratch/dist.txt"

echo 'MASH_CONSUMER_SUMMARY checks=5 fails=0'
