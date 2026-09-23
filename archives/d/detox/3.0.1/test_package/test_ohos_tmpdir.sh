#!/usr/bin/env bash
set -euo pipefail

DETOX=${1:?missing detox executable}
WORK_PARENT=${TMPDIR:-$PWD}
BASE=$(mktemp -d "$WORK_PARENT/detox-conan-test.XXXXXX")
trap 'rm -rf "$BASE"' EXIT

mkdir "$BASE/tmp"
export TMPDIR="$BASE/tmp"

test -d "$TMPDIR"
test -w "$TMPDIR"

touch "$BASE/Harmony OS file.txt"
$DETOX "$BASE/Harmony OS file.txt"

test ! -e "$BASE/Harmony OS file.txt"
test -f "$BASE/Harmony_OS_file.txt"

printf 'HarmonyOS TMPDIR and filename test passed\n'
