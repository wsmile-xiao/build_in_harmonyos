#!/bin/sh
set -eu
binary=$1
alignment=$2
"$binary" -i "$alignment" -d nt -m JC69 -b 0 -c 1
tree="${alignment}_phyml_tree.txt"
test -s "$tree"
grep -q '(' "$tree"
printf 'PHYML_CONSUMER_PASS\n'
