#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the ries executable.
#
# Upstream ships no test suite (GNUmakefile defines only the `ries`, `install`
# and `clean` targets — see MANIFEST.yml), so every case below is a real
# invocation of the *installed* binary through Conan's run environment.
#
# Note on exit codes: RIES deliberately exits non-zero on several normal
# completion paths (e.g. -n early stop returns 242), so cases assert on stdout
# and only pin the exit code where the source makes it deterministic.
set -u

# Scratch files go to TMPDIR (OHOS: /tmp is read-only), never into the archive.
WORK="${TMPDIR:-$HOME/tmp}/ries-test.$$"
mkdir -p "$WORK" || WORK=.
trap 'rm -rf "$WORK"' EXIT

total=0
passed=0
failed=0

ok()   { printf '[test] PASS %s\n' "$1"; passed=$((passed + 1)); }
bad()  { printf '[test] FAIL %s\n' "$1"; failed=$((failed + 1)); }
check() { total=$((total + 1)); if [ "$1" = "0" ]; then ok "$2"; else bad "$2"; fi; }

echo "[test] ries on PATH: $(command -v ries || echo MISSING)"

# 1. --version works and reports the pinned upstream build.
ries --version > "$WORK/out1.txt" 2>&1; rc=$?
grep -q "ries version of 2018 Aug 12" "$WORK/out1.txt" && [ "$rc" = "0" ]; check $? "--version reports 2018 Aug 12"

# 2. --max-matches limits the result set to exactly 3 equations.
ries -n3 2.5063 > "$WORK/out2.txt" 2>&1
n=$(grep -c "for x = " "$WORK/out2.txt")
grep -q "3 matches were found" "$WORK/out2.txt" && [ "$n" = "3" ]; check $? "-n3 2.5063 yields exactly 3 matches"

# 3. Rational search finds the exact identity x = 4.
ries -r 4 > "$WORK/out3.txt" 2>&1
grep -q "x = 4" "$WORK/out3.txt" && grep -q "exact" "$WORK/out3.txt"; check $? "-r 4 finds the exact rational identity"

# 4. Integer search finds x = 4 as well.
ries -i 4 > "$WORK/out4.txt" 2>&1
grep -q "x = 4" "$WORK/out4.txt"; check $? "-i 4 finds the integer identity"

# 5. Algebraic-only search still reports the known 2 x = 5 match.
ries -a 2.5063 > "$WORK/out5.txt" 2>&1
grep -q "2 x = 5" "$WORK/out5.txt"; check $? "-a 2.5063 reports 2 x = 5"

# 6. Symbol table dump is populated.
ries -S > "$WORK/out6.txt" 2>&1; rc=$?
lines=$(wc -l < "$WORK/out6.txt")
[ "$rc" = "0" ] && [ "$lines" -gt 30 ] && grep -q "description" "$WORK/out6.txt"; check $? "-S lists the symbol table ($lines lines)"

# 7. Missing target value is rejected with usage output (deterministic rc=1).
echo "" | ries > "$WORK/out7.txt" 2>&1; rc=$?
grep -q "Please specify a target number" "$WORK/out7.txt" && [ "$rc" = "1" ]; check $? "no target value -> usage error (rc=1)"

# 8. Unknown option is rejected (deterministic rc=255 from print_end(-1)).
ries --definitely-not-an-option 2.5 > "$WORK/out8.txt" 2>&1; rc=$?
grep -q "Unknown option" "$WORK/out8.txt" && [ "$rc" = "255" ]; check $? "unknown option -> Unknown option (rc=255)"

# 9. Search determinism: repeating the same command must reproduce the whole
#    summary byte for byte -- equation list, max complexity, dead-ends,
#    expressions, distinct, Memory and "Total equations tested" -- *except*
#    the program's own wall-clock stopwatch, which ries.c prints from
#    print_end() as  printf("  Time: %.3f\n", tsec)  with tsec = gettime()
#    (ries.c:7511 and :7540 of the pinned 2018.08.05 source) and which no CLI
#    option can suppress.  Measured on the HarmonyOS PC build host: 30 plain
#    runs of `ries -n3 2.5063` give 2 distinct full-output md5 sums (the field
#    reads 0.000 or 0.001) and exactly 1 distinct md5 once that one field is
#    normalised; with a competing CPU load the raw `cmp` of two runs already
#    differs on the `dead-ends: ... Time:` line alone.
#    So the stopwatch *value* is normalised (field level, never the whole
#    line), and the positive control re-checks the same two normalised texts
#    with diff: every difference that survives the field-level mask is a
#    failure, whatever line it sits on.  A whole-line `grep -v Time:` exclusion
#    was rejected because ries prints the stopwatch on the same line as the
#    dead-ends counters (line 13: `dead-ends: 2581 1907 4488  Time: 0.001`),
#    so it would have waved through non-clock differences on that line.
ries -n3 2.5063 > "$WORK/out9a.txt" 2>&1
ries -n3 2.5063 > "$WORK/out9b.txt" 2>&1
sed -E 's/Time:[[:space:]]*[0-9][0-9.]*/Time: <elapsed>/' "$WORK/out9a.txt" > "$WORK/norm9a.txt"
sed -E 's/Time:[[:space:]]*[0-9][0-9.]*/Time: <elapsed>/' "$WORK/out9b.txt" > "$WORK/norm9b.txt"
cmp -s "$WORK/norm9a.txt" "$WORK/norm9b.txt"; norm_rc=$?
diff "$WORK/norm9a.txt" "$WORK/norm9b.txt" \
  | grep -vE '^[0-9]+(,[0-9]+)?[acd][0-9]+(,[0-9]+)?$|^---$' > "$WORK/undisposed9.txt"
[ "$norm_rc" = "0" ] && [ ! -s "$WORK/undisposed9.txt" ]
check $? "-n3 re-run byte-identical except the Time: stopwatch field"

printf '[test] RIES_TEST_SUMMARY total=%d passed=%d failed=%d\n' "$total" "$passed" "$failed"
[ "$failed" = "0" ] || exit 1
exit 0
