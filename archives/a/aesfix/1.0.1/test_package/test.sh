#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
  echo "usage: test.sh AESFIX_BINARY SAMPLE_SCHEDULE" >&2
  exit 2
fi

aesfix_bin=$1
sample=$2

if [ ! -x "$aesfix_bin" ]; then
  echo "aesfix binary is not executable: $aesfix_bin" >&2
  exit 2
fi

if [ ! -f "$sample" ]; then
  echo "sample schedule not found: $sample" >&2
  exit 2
fi

set +e
output=$("$aesfix_bin" "$sample" 2>&1)
status=$?
set -e

printf "%s\n" "$output"

if [ "$status" -ne 1 ]; then
  echo "expected aesfix sample run to exit 1 after finding a corrected schedule, got $status" >&2
  exit 1
fi

case "$output" in
  *"corrected key schedule"*) ;;
  *)
    echo "aesfix output did not include corrected key schedule marker" >&2
    exit 1
    ;;
esac

case "$output" in
  *"91287ACD F26EC559 82DC89D3 6C7111E6"*) ;;
  *)
    echo "aesfix output did not include expected corrected first row" >&2
    exit 1
    ;;
esac
