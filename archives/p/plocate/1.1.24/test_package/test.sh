#!/bin/sh
# End-to-end consumer verification for plocate 1.1.24 on OHOS.
# Builds a database from a known plaintext file list (updatedb -p, no root
# needed) and asserts real query behavior of the installed plocate binary.
set -eu
count() { awk 'END{print NR+0}'; }

work=$(pwd)/e2ework
rm -rf "$work"
mkdir -p "$work/corpus/reports" "$work/corpus/data"
: > "$work/corpus/reports/alpha_report.txt"
: > "$work/corpus/reports/beta.md"
: > "$work/corpus/data/alpha notes.txt"
: > "$work/corpus/data/gamma.bin"

for b in plocate plocate-build updatedb; do
    command -v "$b" >/dev/null 2>&1 || { echo "FAIL: $b not on PATH"; exit 1; }
done
pass=0

# 1. version string
out=$(plocate --version | head -1)
[ "$out" = "plocate 1.1.24" ] || { echo "FAIL 1: --version [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 1: --version -> $out"

# 2. build database from plaintext list (plocate-build -p IN OUT)
find "$work/corpus" -type f | sort > "$work/list.txt"
[ "$(< "$work/list.txt" count)" = "4" ] || { echo "FAIL 2a: list size"; exit 1; }
plocate-build -p "$work/list.txt" "$work/plocate.db"
[ -s "$work/plocate.db" ] || { echo "FAIL 2b: db not created"; exit 1; }
pass=$((pass+1)); echo "PASS 2: plocate-build -p built db ($(wc -c < "$work/plocate.db" | tr -d " ") bytes)"

# 3. two-file match, whole-path search
out=$(plocate -N -d "$work/plocate.db" alpha | sort)
exp="$work/corpus/data/alpha notes.txt
$work/corpus/reports/alpha_report.txt"
[ "$out" = "$exp" ] || { echo "FAIL 3: [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 3: query 'alpha' -> 2 exact matches"

# 4. case-insensitive
n=$(plocate -N -i -d "$work/plocate.db" ALPHA | count)
[ "$n" = "2" ] || { echo "FAIL 4: -i matched $n"; exit 1; }
pass=$((pass+1)); echo "PASS 4: -i ALPHA -> 2"

# 5. --count agrees with listing
n=$(plocate -c -d "$work/plocate.db" alpha)
[ "$n" = "2" ] || { echo "FAIL 5: -c gave [$n]"; exit 1; }
pass=$((pass+1)); echo "PASS 5: -c alpha -> 2"

# 6. basename-only search
out=$(plocate -N -b -d "$work/plocate.db" alpha_report.txt)
[ "$out" = "$work/corpus/reports/alpha_report.txt" ] || { echo "FAIL 6: -b [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 6: -b alpha_report.txt -> 1"

# 7. regex search over full path
n=$(plocate -N -r -d "$work/plocate.db" "^$work/corpus/reports/" | count)
[ "$n" = "2" ] || { echo "FAIL 7: -r matched $n"; exit 1; }
pass=$((pass+1)); echo "PASS 7: -r '^...reports/' -> 2"

# 8. limit
n=$(plocate -N -l 1 -d "$work/plocate.db" alpha | count)
[ "$n" = "1" ] || { echo "FAIL 8: -l 1 gave $n"; exit 1; }
pass=$((pass+1)); echo "PASS 8: -l 1 -> 1 line"

# 9. no match yields empty output
out=$(plocate -N -d "$work/plocate.db" zzqqxxnomatch || true)
[ -z "$out" ] || { echo "FAIL 9: unexpected [$out]"; exit 1; }
pass=$((pass+1)); echo "PASS 9: missing pattern -> empty"

# 10. all four files recoverable via empty-ish broad query (ext glob)
n=$(plocate -N --regex -d "$work/plocate.db" "$work/corpus/.*" | count)
[ "$n" = "4" ] || { echo "FAIL 10: regex-all gave $n"; exit 1; }
pass=$((pass+1)); echo "PASS 10: regex over corpus root -> 4"

echo "test plocate 1.1.24: $pass/10 checks PASS"
exit 0
