#!/bin/sh
set -eu

printf '%s\n' \
  '192.0.2.0/25' \
  '192.0.2.128/25' \
  '198.51.100.0/24' | aggregate > output.txt

grep -Fxq '192.0.2.0/24' output.txt
grep -Fxq '198.51.100.0/24' output.txt
test "$(wc -l < output.txt | tr -d ' ')" = "2"
