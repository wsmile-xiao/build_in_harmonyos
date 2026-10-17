#!/bin/sh
# test_tarlz.sh — tarlz 0.29 consumer roundtrip (real binary, real asserts).
# 1. tarlz --version runs. 2. create .tar.lz from fixtures. 3. list shows
# members. 4. extract + byte-compare with originals.
set -u
BIN="${1:-tarlz}"
WORK="$PWD/tarlz-test"
rm -rf "$WORK"; mkdir -p "$WORK/fixture/sub"
cd "$WORK" || exit 1

echo "hello tarlz" > fixture/greeting.txt
printf 'a%.0s' $(seq 1 2000) > fixture/blob.bin
echo "nested" > fixture/sub/nested.txt

"$BIN" --version > version.txt 2>&1 || { echo "FAIL: --version rc=$?"; exit 1; }
grep -qi "tarlz" version.txt || { echo "FAIL: no tarlz in --version"; cat version.txt; exit 1; }
echo "PASS: version: $(head -1 version.txt)"

"$BIN" -c -f roundtrip.tar.lz fixture || { echo "FAIL: create rc=$?"; exit 1; }
[ -s roundtrip.tar.lz ] || { echo "FAIL: archive empty"; exit 1; }
echo "PASS: archive created ($(wc -c < roundtrip.tar.lz) bytes)"

"$BIN" -t -f roundtrip.tar.lz > members.txt || { echo "FAIL: list rc=$?"; exit 1; }
grep -q "greeting.txt" members.txt || { echo "FAIL: greeting missing"; cat members.txt; exit 1; }
grep -q "nested.txt" members.txt || { echo "FAIL: nested missing"; cat members.txt; exit 1; }
echo "PASS: members listed ($(wc -l < members.txt) entries)"

mkdir out && "$BIN" -x -f roundtrip.tar.lz -C out || { echo "FAIL: extract rc=$?"; exit 1; }
cmp fixture/greeting.txt out/fixture/greeting.txt || { echo "FAIL: greeting differs"; exit 1; }
cmp fixture/blob.bin out/fixture/blob.bin || { echo "FAIL: blob differs"; exit 1; }
cmp fixture/sub/nested.txt out/fixture/sub/nested.txt || { echo "FAIL: nested differs"; exit 1; }
echo "PASS: extract byte-identical (3/3)"
echo "TARLZ_TEST PASS"
