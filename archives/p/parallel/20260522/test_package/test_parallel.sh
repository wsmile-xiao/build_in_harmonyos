#!/usr/bin/env zsh
set -euo pipefail
zmodload zsh/datetime
parallel=$1
perl=$2

test -x "$parallel"
test -x "$perl"
"$perl" "$parallel" --version | grep -F "GNU parallel 20260522"

start=$EPOCHREALTIME
actual=$(printf '%s\n' 2 1 | "$perl" "$parallel" --will-cite -j 2 'sleep 3; printf "%s\\n" {}' | sort)
elapsed=$(( EPOCHREALTIME - start ))
expected=$(printf '%s\n' 1 2)
test "$actual" = "$expected"
(( elapsed < 5.5 ))
printf 'PASS: two 3-second jobs completed concurrently in %.3f seconds\n' "$elapsed"
