#!/bin/sh
set -eu

barcode="$1"
output="barcode.svg"

# -S selects SVG output; -b gives the data to encode; -e selects Code 128.
"$barcode" -S -b 1234567890 -e code128 -o "$output"
grep -q '<svg' "$output"
grep -q '1234567890' "$output"
rm -f "$output"
