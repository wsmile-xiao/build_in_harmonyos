#!/bin/sh
set -eu

binary=$1
data=$2

"$binary" -V
"$binary" mw -b -d "$data" 0 0x41 0x42 0x43 0x44
output=$("$binary" md -b -s "$data" 0+4)
printf '%s\n' "$output" | grep "41 42 43 44"
