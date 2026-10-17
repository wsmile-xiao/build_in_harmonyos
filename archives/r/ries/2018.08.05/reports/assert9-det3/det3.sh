#!/data/service/hnp/bin/bash
# det3.sh - evidence: is the Time field in ries -n3 output volatile?
set -u
export PATH="$HOME/usr/local/bin:$HOME/.local/bin:$PATH"
BIN="$1"
N="${2:-30}"
W="$HOME/tmp/uc2/z45-ries/det3"
rm -rf "$W"; mkdir -p "$W" || { echo "WORKDIR FAIL"; exit 9; }
cd "$W" || exit 9

SRC="$HOME/tmp/ch/home-ries/p/ries58ff4b50a30d0/s/ries.c"
echo "=== source sites that print time/memory ==="
grep -n -E 'Time:|Memory:|sec so far' "$SRC" | head -20

echo "=== $N plain runs of: ries -n3 2.5063 ==="
: > times.txt
: > md_full.txt
: > md_mask.txt
i=1
while [ "$i" -le "$N" ]; do
  "$BIN" -n3 2.5063 > "o$i.txt" 2>&1
  echo "rc$i=$?"
  tv=`grep -o 'Time: [0-9.]*' "o$i.txt" | head -1`
  mv=`grep -o 'Memory: [0-9]* B' "o$i.txt" | head -1`
  a=`md5sum < "o$i.txt" | cut -c1-10`
  sed -E 's/Time:[[:space:]]*[0-9.]+/Time: X/' "o$i.txt" | md5sum | cut -c1-10 > tmpmask
  b=`cat tmpmask`
  printf 'run%-3s %-12s %-14s full=%s masked=%s\n' "$i" "$tv" "$mv" "$a" "$b"
  echo "$tv" >> times.txt
  echo "$a" >> md_full.txt
  echo "$b" >> md_mask.txt
  i=`expr $i + 1`
done

echo "=== distinct counts over $N runs ==="
echo "full-output distinct   : `sort -u md_full.txt | wc -l`"
echo "time-masked distinct   : `sort -u md_mask.txt | wc -l`"
echo "distinct Time strings  : `sort -u times.txt | wc -l`"
echo "Time values seen       : `tr '\n' ' ' < times.txt`"

echo "=== two runs while a busy competitor holds a core ==="
i=0
while [ "$i" -lt 3000000 ]; do i=`expr $i + 1`; done &
busy=$!
sleep 1
"$BIN" -n3 2.5063 > load_a.txt 2>&1; echo "rcA=$?"
"$BIN" -n3 2.5063 > load_b.txt 2>&1; echo "rcB=$?"
kill $busy 2>/dev/null
grep -o 'Time: [0-9.]*' load_a.txt
grep -o 'Time: [0-9.]*' load_b.txt
cmp -s load_a.txt load_b.txt; echo "raw cmp rc (0=ident) = $?"
sed -E 's/Time:[[:space:]]*[0-9.]+/Time: X/' load_a.txt > la.txt
sed -E 's/Time:[[:space:]]*[0-9.]+/Time: X/' load_b.txt > lb.txt
cmp -s la.txt lb.txt; echo "masked cmp rc (0=ident) = $?"
echo "=== diff of the loaded pair ==="
diff load_a.txt load_b.txt
echo DETDONE
