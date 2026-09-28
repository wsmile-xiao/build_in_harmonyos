#!/bin/sh
# test_package/test.sh — consumer test for the INSTALLED yapet CLI tools (8 cases).
#
# Driven by test_package/conanfile.py `test()` via `self.run(..., env="conanrun")`.
# Cases are the same eight assertions this package has always claimed:
#   1. yapet -V      rc=0 AND output self-reports 2.6
#   2. yapet -h      rc=0
#   3. csv2yapet -V  rc=0 AND output self-reports 2.6
#   4. yapet2csv -V  rc=0 AND output self-reports 2.6
#   5. csv2yapet encrypts input.csv into a non-empty .pet
#   6. yapet2csv decrypts it back byte-identical to input.csv
#   7. a wrong master password is rejected (rc != 0)
#   8. an unknown option is rejected (rc != 0)
#
# All file arguments are absolute paths: conan 2 runs test_package IN-PLACE
# inside the worktree, so pwd-relative paths would either not resolve or drop
# runtime junk into the commit surface (caught once by stage_candidate
# reconciliation — precedent cdcd/integrit).  Case 5/6 artifacts go to the
# isolated work dir passed as $2 (conanfile builds it under TMPDIR, never the
# real HOME and never the worktree).
set -u

BIN="${1:?usage: test.sh <installed-bin-dir> <isolated-work-dir> <input.csv>}"
WORK="${2:?usage: test.sh <installed-bin-dir> <isolated-work-dir> <input.csv>}"
INPUT="${3:?usage: test.sh <installed-bin-dir> <isolated-work-dir> <input.csv>}"

YAPET="$BIN/yapet"
CSV2YAPET="$BIN/csv2yapet"
YAPET2CSV="$BIN/yapet2csv"
PW='s3cret-pw!'
PASS=0
FAIL=0
TOTAL=8

ok()   { PASS=$((PASS+1)); echo "case $((PASS+FAIL))/$TOTAL ok: $1"; }
bad()  { FAIL=$((FAIL+1)); echo "case $((PASS+FAIL))/$TOTAL FAIL: $1"; }

for b in "$YAPET" "$CSV2YAPET" "$YAPET2CSV"; do
  if [ ! -f "$b" ]; then echo "FATAL: missing installed tool $b"; exit 1; fi
done
[ -f "$INPUT" ] || { echo "FATAL: missing fixture $INPUT"; exit 1; }
mkdir -p "$WORK" 2>/dev/null || true
[ -d "$WORK" ] || { echo "FATAL: isolated work dir not creatable: $WORK"; exit 1; }

# case 1-4: runnable AND self-report the claimed version (not just rc==0 —
# a stale/foreign binary would still exit 0)
for spec in "1:yapet -V:$YAPET:-V" "3:csv2yapet -V:$CSV2YAPET:-V" "4:yapet2csv -V:$YAPET2CSV:-V"; do
  idx=${spec%%:*}; rest=${spec#*:}
  what=${rest%%:*}; rest=${rest#*:}
  bin=${rest%%:*}; opt=${rest##*:}
  out="$WORK/case$idx.out"
  if ! "$bin" "$opt" > "$out" 2>&1; then
    bad "$what exited non-zero: $(head -c 120 "$out")"
    continue
  fi
  if grep -q '2\.6' "$out"; then
    ok "$what rc=0 and self-reports 2.6"
  else
    bad "$what did not self-report 2.6: $(head -c 120 "$out")"
  fi
done
# yapet -h: exit code only (usage text, no version claim needed)
if "$YAPET" -h > "$WORK/case2.out" 2>&1; then ok "yapet -h exit 0"; else bad "yapet -h non-zero"; fi

PET="$WORK/roundtrip.pet"
CSVOUT="$WORK/roundtrip.csv"
rm -f "$PET" "$CSVOUT"
# case 5: encrypt fixture → non-empty .pet
if "$CSV2YAPET" -q -p "$PW" -s , "$INPUT" "$PET" > "$WORK/case5.out" 2>&1 \
   && [ -f "$PET" ] && [ -s "$PET" ]; then
  ok "csv2yapet wrote non-empty $(basename "$PET") ($(wc -c < "$PET") B)"
else
  bad "csv2yapet did not produce a non-empty .pet: $(head -c 160 "$WORK/case5.out")"
fi
# case 6: decrypt back → byte identical
if [ -f "$PET" ] && "$YAPET2CSV" -q -p "$PW" -s , "$PET" "$CSVOUT" > "$WORK/case6.out" 2>&1 \
   && cmp -s "$INPUT" "$CSVOUT"; then
  ok "csv2yapet/yapet2csv roundtrip byte-identical"
else
  bad "roundtrip mismatch (cmp rc=$?): $(head -c 160 "$WORK/case6.out" 2>/dev/null)"
fi
# case 7: wrong master password rejected
if [ -f "$PET" ]; then
  if "$YAPET2CSV" -q -p "wrong-password" -s , "$PET" "$WORK/wrong.csv" > "$WORK/case7.out" 2>&1; then
    bad "yapet2csv accepted a wrong master password"
  else
    ok "wrong master password rejected (rc=$?)"
  fi
else
  bad "case 7 skipped: no .pet from case 5"
fi
# case 8: unknown option rejected (getopt error path)
if "$YAPET" -Z > "$WORK/case8.out" 2>&1; then
  bad "yapet accepted an unknown option"
else
  ok "unknown option rejected (rc=$?)"
fi

echo "[consumer] PASS=$PASS FAIL=$FAIL TOTAL=$TOTAL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
