#!/usr/bin/env sh
set -eu
binary=$1
expected=$2
output=$("$binary" --version)
printf '%s\n' "$output"
case "$output" in
  *"$expected"*) ;;
  *)
    echo "version output did not contain $expected" >&2
    exit 1
    ;;
esac
