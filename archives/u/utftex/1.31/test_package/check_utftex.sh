#!/usr/bin/env bash
set -euo pipefail

utftex="$1"
test -x "$utftex"
output=$("$utftex" '\frac{a}{b}')
test -n "$output"
echo "PASS utftex formula smoke"
