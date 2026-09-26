#!/bin/sh
# Consumer-view end-to-end test for the packaged pcb2gcode command line tool.
#
# Converts a real KiCad Gerber sample (outline + front copper + millproject,
# taken from the upstream test data tests/data/gerbv_example/backtrack) into
# G-code and validates the produced files.
#
# Usage: test_pcb2gcode.sh <pcb2gcode-exe> <data-dir> <work-dir>
set -eu

EXE="$1"
DATA_DIR="$2"
WORKDIR="$3"

echo "== pcb2gcode consumer test =="
echo "binary: $EXE"

test -f "$EXE" || { echo "FAIL: binary not found: $EXE"; exit 1; }

# 1) version banner (pure I/O exit path; also prints the linked Boost/gerbv/GEOS)
"$EXE" --version

# 2) real Gerber -> G-code conversion
mkdir -p "$WORKDIR"
cp "$DATA_DIR"/* "$WORKDIR"/
cd "$WORKDIR"
"$EXE" --config=millproject

# 3) validate the produced G-code
COUNT=0
for f in "$WORKDIR"/*.nc; do
    [ -f "$f" ] || continue
    COUNT=$((COUNT + 1))
    test -s "$f" || { echo "FAIL: empty G-code file: $f"; exit 1; }
    grep -q "G0" "$f" || { echo "FAIL: no G-code motion command in $f"; exit 1; }
done
test "$COUNT" -ge 1 || { echo "FAIL: no .nc output produced"; exit 1; }

echo "OK: produced $COUNT G-code file(s)"
ls -l "$WORKDIR"/*.nc
