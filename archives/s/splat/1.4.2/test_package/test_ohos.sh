#!/bin/sh
set -eu

bindir=$1
workdir=${TMPDIR:-$PWD}
case "$workdir" in
    /tmp|/tmp/*) echo "OHOS test must not use /tmp" >&2; exit 1 ;;
esac

testdir="$workdir/splat-ohos-test-$$"
mkdir -p "$testdir"
trap 'rm -rf "$testdir"' EXIT HUP INT TERM

"$bindir/usgs2sdf" > "$testdir/usgs.out" 2>&1
grep -q "Usage: usgs2sdf" "$testdir/usgs.out"
