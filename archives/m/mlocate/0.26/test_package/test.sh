#!/usr/bin/env bash
# Verify that the packaged locate and updatedb can create and query a database.
set -euo pipefail
umask 022

if [ -z "${MLOCATE_BINDIR:-}" ]; then
    echo "MLOCATE_BINDIR is not set" >&2
    exit 1
fi
PATH="$MLOCATE_BINDIR:$PATH"
export PATH

work="$PWD/.mlocate-test-$$"
mkdir "$work"
trap 'rm -rf "$work"' 0

source_root="$work/source"
mkdir -p "$source_root/subdir"
marker="harmony-mlocate-probe-$$"
: > "$source_root/subdir/$marker"

locate_version="$(locate --version 2>&1)"
case "$locate_version" in
    *"mlocate 0.26"*) echo "        [ok] locate version" ;;
    *) echo "        [fail] locate version: $locate_version"; exit 1 ;;
esac

updatedb_version="$(updatedb --version 2>&1)"
case "$updatedb_version" in
    *"0.26"*) echo "        [ok] updatedb version" ;;
    *) echo "        [fail] updatedb version: $updatedb_version"; exit 1 ;;
esac

updatedb -U "$source_root" -o "$work/mlocate.db" -l 0
test -s "$work/mlocate.db"
echo "        [ok] updatedb creates a database"

actual="$(locate -d "$work/mlocate.db" "$marker")"
expected="$source_root/subdir/$marker"
test "$actual" = "$expected"
echo "        [ok] locate finds a path from the generated database"

echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test.sh","consumer_passed":4,"consumer_total":4}'
