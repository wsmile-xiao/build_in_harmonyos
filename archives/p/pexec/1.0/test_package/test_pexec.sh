#!/bin/sh
# Consumer test for pexec (HarmonyOS PC / OHOS aarch64).
#
# Exercises the real parallel-execution semantics of the installed binary, not
# just the option-parsing smoke paths. On OHOS the classic /bin/sh is not
# guaranteed to exist, so the shell handed to pexec is discovered here and
# passed explicitly with -s; that lookup is part of what this test pins down.
#
#   usage: sh test_pexec.sh <path to installed pexec binary>

PEXEC="$1"
WORK="${TMPDIR:-$PWD}/pexec-consumer-$$"
PASS=0
FAIL=0

ok()  { PASS=$((PASS+1)); echo "  ok   - $1"; }
bad() { FAIL=$((FAIL+1)); echo "  FAIL - $1"; }
chk() { if [ "$1" -eq 0 ]; then ok "$2"; else bad "$2 (rc=$1)"; fi; }

if [ ! -x "$PEXEC" ]; then
    echo "pexec binary not found or not executable: $PEXEC" >&2
    exit 1
fi

SH=""
for cand in /bin/sh /system/bin/sh /data/service/hnp/bin/sh; do
    if [ -x "$cand" ]; then SH="$cand"; break; fi
done
if [ -z "$SH" ]; then
    SH="$(command -v sh 2>/dev/null || command -v bash 2>/dev/null || true)"
fi
if [ -z "$SH" ]; then
    echo "no shell available to drive pexec -c" >&2
    exit 1
fi
echo "  using shell for -c: $SH"

rm -rf "$WORK"
mkdir -p "$WORK" || exit 1
cd "$WORK" || exit 1

PARAMS="alpha
beta
gamma"

# 1) --help: exit 0, prints the tool banner
"$PEXEC" --help >help.out 2>&1
chk $? "[1] --help exits 0"
grep -qi pexec help.out
chk $? "[2] --help mentions pexec"

# 2) --version: exit 0 and reports a version string
"$PEXEC" --version >ver.out 2>&1
chk $? "[3] --version exits 0"
grep -qiE 'pexec.*[0-9]|[0-9].*pexec' ver.out
chk $? "[4] --version reports a version"

# 3) unknown option is rejected with a non-zero exit code
if "$PEXEC" --definitely-not-an-option >/dev/null 2>&1; then
    chk 1 "[5] unknown option rejected"
else
    chk 0 "[5] unknown option rejected"
fi

# 4) parallel fan-out: one parameter per process, each job gets its parameter
#    through the environment (-e) and its own stdout file (-o format).
pexec_run() {
    "$PEXEC" -p "$PARAMS" -e PEXEC_PARAM -o "res-%s.txt" -n "$1" -s "$SH" -c -- \
        'printf "param=%s\n" "$PEXEC_PARAM"'
}

pexec_run 3 >run3.out 2>&1
chk $? "[6] parallel run (-n 3) exits 0"

NFILES=$(ls res-*.txt 2>/dev/null | wc -l | tr -d ' ')
if [ "$NFILES" = "3" ]; then ok "[7] three parameters -> three result files"; else bad "[7] expected 3 result files, got $NFILES"; fi

for p in alpha beta gamma; do
    if [ -f "res-$p.txt" ] && [ "$(cat "res-$p.txt")" = "param=$p" ]; then
        ok "[8] res-$p.txt holds the right parameter"
    else
        bad "[8] res-$p.txt missing or wrong: $(cat "res-$p.txt" 2>/dev/null)"
    fi
done

# 5) the same work must come out identically when serialized (-n 1)
rm -f res-*.txt
pexec_run 1 >run1.out 2>&1
chk $? "[9] serialized run (-n 1) exits 0"
SAME=1
for p in alpha beta gamma; do
    [ -f "res-$p.txt" ] || SAME=0
    [ "$(cat "res-$p.txt" 2>/dev/null)" = "param=$p" ] || SAME=0
done
chk $((1-SAME)) "[10] -n 1 produces the same three results as -n 3"

# 6) parameter list read from a file (-f) instead of -p
printf '%s\n' "$PARAMS" > list.txt
rm -f res-*.txt
"$PEXEC" -f list.txt -e PEXEC_PARAM -o "res-%s.txt" -n 2 -s "$SH" -c -- \
    'printf "param=%s\n" "$PEXEC_PARAM"' >runf.out 2>&1
chk $? "[11] parameter list from file (-f) exits 0"
NFILES=$(ls res-*.txt 2>/dev/null | wc -l | tr -d ' ')
if [ "$NFILES" = "3" ]; then ok "[12] -f drives the same three jobs"; else bad "[12] -f produced $NFILES result files"; fi

# 7) -R gathers every job's stdout into the parent stream: exactly one line each
"$PEXEC" -R -p "$PARAMS" -e PEXEC_PARAM -n 3 -s "$SH" -c -- \
    'printf "line-%s\n" "$PEXEC_PARAM"' >merged.out 2>&1
chk $? "[13] merged-stdout run (-R) exits 0"
NLINES=$(grep -c '^line-' merged.out 2>/dev/null || echo 0)
if [ "$NLINES" = "3" ]; then ok "[14] merged stdout holds exactly 3 job lines"; else bad "[14] merged stdout has $NLINES lines"; fi

rm -rf "$WORK"

echo "TOTAL=$((PASS+FAIL)) PASS=$PASS FAIL=$FAIL"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
echo "pexec consumer tests passed"
