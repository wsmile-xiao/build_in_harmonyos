#!/bin/sh
set -euo pipefail

bin_dir=$1

pll_output=$("$bin_dir/icepll" -i 12 -o 48)
case "$pll_output" in
  *F_PLLIN*) ;;
  *) exit 1 ;;
esac

for tool in icepack icemulti icebram icetime; do
  status=0
  output=$("$bin_dir/$tool" -h 2>&1) || status=$?
  [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
  case "$output" in
    *Usage:*) ;;
    *) exit 1 ;;
  esac
done

test -x "$bin_dir/iceunpack"
