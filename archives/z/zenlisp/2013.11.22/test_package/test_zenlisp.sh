#!/bin/sh
set -eu

ZL=$1

test -x "$ZL"
test -f "${ZENLISP_IMAGE}"
test -f "${ZENSRC}/base.l"

result=$(printf '%s\n' "(car '#ab)" | "$ZL" -b -n 12K)
test "$result" = "'a"

math_result=$(printf '%s\n' "(load ~nmath) (+ '#2 '#3)" | "$ZL" -b -n 12K)
printf '%s\n' "$math_result" | grep -Fqx "'#5"

"$ZL" -L | grep -Fq "zenlisp -- An interpreter for symbolic LISP"
