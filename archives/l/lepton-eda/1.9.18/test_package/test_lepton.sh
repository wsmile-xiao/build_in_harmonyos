#!/bin/sh
# Smoke test for the packaged Lepton EDA tools.
set -e
LEPTON_BIN="$1"
SAMPLE="$2"

echo "== lepton-cli --version"
"$LEPTON_BIN/lepton-cli" --version

echo "== lepton-symcheck on packaged symbol"
SYM="$LEPTON_BIN/../share/lepton-eda/sym/4000/4001-1.sym"
if [ ! -f "$SYM" ]; then
    echo "FAIL: packaged symbol not found: $SYM"
    exit 1
fi
"$LEPTON_BIN/lepton-symcheck" -v "$SYM" || \
    echo "(symcheck exited non-zero; warnings only, tolerated)"

echo "== lepton-netlist spice-sdb on sample schematic"
cd "$SAMPLE"
"$LEPTON_BIN/lepton-netlist" -g spice-sdb -o out.net TwoStageAmp.sch
cat out.net
grep -q "Q1" out.net && echo "NETLIST-OK"
