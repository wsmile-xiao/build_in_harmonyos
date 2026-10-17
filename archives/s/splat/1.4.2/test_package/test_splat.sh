#!/bin/sh
set -eu

bindir=$1

for command in splat splat-hd citydecoder usgs2sdf srtm2sdf srtm2sdf-hd fontdata bearing; do
    test -x "$bindir/$command"
done

workdir=${TMPDIR:-$PWD}
testdir="$workdir/splat-test-$$"
mkdir -p "$testdir"
trap 'rm -rf "$testdir"' EXIT HUP INT TERM

cat > "$testdir/site-a.qth" <<'EOF'
Site A
0.0
0.0
10
EOF
cat > "$testdir/site-b.qth" <<'EOF'
Site B
0.0
1.0
10
EOF

(
    cd "$testdir"
    "$bindir/bearing" site-a site-b -metric > bearing.out
)
grep -q "Site A" "$testdir/bearing.out"
grep -q "Site B" "$testdir/bearing.out"
grep -q "kilometers" "$testdir/bearing.out"

if "$bindir/splat" > "$testdir/splat.out" 2>&1; then
    :
fi
grep -q "SPLAT!" "$testdir/splat.out"
grep -q "SPLAT! v1.4.2 Available Options" "$testdir/splat.out"

if "$bindir/splat-hd" > "$testdir/splat-hd.out" 2>&1; then
    :
fi
grep -q "SPLAT! HD v1.4.2 Available Options" "$testdir/splat-hd.out"
