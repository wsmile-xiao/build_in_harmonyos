#!/usr/bin/env bash
set -euo pipefail

DETOX=${1:?missing detox executable}
INLINE_DETOX=${2:?missing inline-detox executable}
WORK_PARENT=${TMPDIR:-$PWD}
WORK=$(mktemp -d "$WORK_PARENT/detox-package-test.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

VERSION_OUTPUT=$($DETOX -V)
test "$VERSION_OUTPUT" = "detox 3.0.1"

INLINE_VERSION_OUTPUT=$($INLINE_DETOX -V)
test "$INLINE_VERSION_OUTPUT" = "detox 3.0.1"

HELP_OUTPUT=$($DETOX -h)
printf '%s\n' "$HELP_OUTPUT" | grep -q "usage: detox"

SEQUENCE_OUTPUT=$($DETOX -L)
printf '%s\n' "$SEQUENCE_OUTPUT" | grep -q "default"

touch "$WORK/dry run.txt"
$DETOX -n "$WORK/dry run.txt"
test -f "$WORK/dry run.txt"
test ! -e "$WORK/dry_run.txt"

$DETOX "$WORK/dry run.txt"
test ! -e "$WORK/dry run.txt"
test -f "$WORK/dry_run.txt"

INLINE_OUTPUT=$(printf 'inline file.txt\n' | $INLINE_DETOX)
test "$INLINE_OUTPUT" = "inline_file.txt"

printf 'detox package consumer tests passed\n'
