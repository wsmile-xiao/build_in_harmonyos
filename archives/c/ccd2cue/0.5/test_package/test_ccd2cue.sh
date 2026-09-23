#!/bin/sh
set -eu

tmp_dir=".ccd2cue-test.$$"
mkdir "$tmp_dir"
trap 'rm -f "$tmp_dir"/sample.ccd "$tmp_dir"/sample.cue "$tmp_dir"/sample.cdt "$tmp_dir"/bad.out "$tmp_dir"/bad.err; rmdir "$tmp_dir"' EXIT

assert_contains() {
    needle=$1
    haystack=$2
    case "$haystack" in
        *"$needle"*) echo "[ok] $needle" ;;
        *) echo "[fail] missing: $needle" >&2; exit 1 ;;
    esac
}

command -v ccd2cue >/dev/null
echo "[ok] ccd2cue is available from the package PATH"

version=$(ccd2cue --version 2>&1)
assert_contains "ccd2cue (GNU ccd2cue) 0.5" "$version"

help=$(ccd2cue --help 2>&1)
assert_contains "Convert CCD sheet to CUE sheet." "$help"

cat > "$tmp_dir/sample.ccd" <<'EOF'
[CloneCD]
Version=3

[Disc]
TocEntries=1
Sessions=1
DataTracksScrambled=0
CDTextLength=0

[Entry 0]
Session=1
Point=a0
ADR=1
Control=4
TrackNo=0
AMin=0
ASec=0
AFrame=0
ALBA=0
Zero=0
PMin=0
PSec=0
PFrame=0
PLBA=0

[Session 1]
PreGapMode=0
PreGapSubC=0

[TRACK 1]
MODE=0
INDEX 0=0
INDEX 1=150
EOF

ccd2cue \
    --output "$tmp_dir/sample.cue" \
    --image sample.bin \
    --cd-text "$tmp_dir/sample.cdt" \
    "$tmp_dir/sample.ccd"
echo "[ok] CCD input converted successfully"

cue=$(cat "$tmp_dir/sample.cue")
assert_contains 'FILE "sample.bin" BINARY' "$cue"
assert_contains 'TRACK 1 AUDIO' "$cue"
assert_contains 'INDEX 01 00:02:00' "$cue"

if ccd2cue --definitely-invalid-option > "$tmp_dir/bad.out" 2> "$tmp_dir/bad.err"; then
    echo "[fail] invalid option unexpectedly succeeded" >&2
    exit 1
fi
echo "[ok] invalid option returns non-zero"

echo "ccd2cue 0.5 consumer test: 8 assertions passed"
