#!/bin/sh
set -eu

mawk=$1

"$mawk" -W version >/dev/null
sum=$(printf '1 2 3 4\n' | "$mawk" '{ for (i = 1; i <= NF; ++i) total += $i } END { print total }')
test "$sum" = "10"
words=$(printf 'red blue red\n' | "$mawk" '{ for (i = 1; i <= NF; ++i) seen[$i]++ } END { print seen["red"], seen["blue"] }')
test "$words" = "2 1"
