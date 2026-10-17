#!/bin/sh
set -eu

bru=$1

version=$("$bru" --version)
test "$version" = "3.4.2"

# --help may exit non-zero on some yargs versions, capture regardless
help_output=$("$bru" --help 2>&1 || true)
echo "$help_output" | grep -q "bru.*run"
echo "$help_output" | grep -q "bru.*import"

echo "bruno-cli consumer tests passed"
