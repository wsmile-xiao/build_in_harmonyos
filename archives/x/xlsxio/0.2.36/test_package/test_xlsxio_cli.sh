#!/bin/sh
# CLI roundtrip test for the xlsxio tools (xlsxio_csv2xlsx / xlsxio_xlsx2csv).
# $1 = package bin dir (falls back to PATH lookup when empty).
set -e

BINDIR="$1"
CSV2XLSX="${BINDIR:+$BINDIR/}xlsxio_csv2xlsx"
XLSX2CSV="${BINDIR:+$BINDIR/}xlsxio_xlsx2csv"

work="${TMPDIR:-.}/xlsxio_cli_test.$$"
mkdir -p "$work"
cd "$work"
trap 'cd /; rm -rf "$work"' EXIT

printf 'name,score\nhello,42\nworld,-7\n' > input.csv

# csv -> xlsx (tool writes <input>.xlsx next to the input)
"$CSV2XLSX" -t input.csv
[ -f input.csv.xlsx ] || { echo "FAIL: csv2xlsx produced no output"; exit 1; }

# xlsx -> csv (tool exports each sheet to <xlsxfile>.<sheetname>.csv)
"$XLSX2CSV" input.csv.xlsx
out=""
for f in input.csv.xlsx.*.csv; do
    [ -f "$f" ] && out="$f"
done
[ -n "$out" ] || { echo "FAIL: xlsx2csv produced no output"; exit 1; }

grep -q 'hello' "$out" || { echo "FAIL: roundtrip lost 'hello'"; exit 1; }
grep -q '42' "$out" || { echo "FAIL: roundtrip lost '42'"; exit 1; }
grep -q 'world' "$out" || { echo "FAIL: roundtrip lost 'world'"; exit 1; }
grep -q -- '-7' "$out" || { echo "FAIL: roundtrip lost '-7'"; exit 1; }

echo "CLI roundtrip: PASS"
