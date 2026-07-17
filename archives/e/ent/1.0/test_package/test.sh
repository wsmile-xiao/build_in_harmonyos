#!/data/service/hnp/bin/bash
set -euo pipefail

WORK="$(pwd)/_ent_test"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

dd if=/dev/zero of=sample.bin bs=2048 count=1 >/dev/null 2>&1

ent sample.bin > out.txt

grep -q "Entropy" out.txt
grep -q "Chi square" out.txt
grep -q "Monte Carlo value for Pi" out.txt
grep -q "Serial correlation coefficient" out.txt

echo "[ok] ent analyzed sample.bin"
