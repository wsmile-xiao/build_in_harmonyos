#!/bin/sh
set -eu

output="$(capstats --version 2>&1)"
printf 'capstats --version => %s\n' "$output"
test "$output" = "capstats 0.31"
