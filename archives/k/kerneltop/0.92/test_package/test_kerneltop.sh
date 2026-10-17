#!/data/service/hnp/bin/bash
# test_package/test_kerneltop.sh - consumer-level functional tests for kerneltop 0.92
#
# kerneltop upstream ships NO test suite at all: the release tarball holds
# exactly 3 files (kerneltop.c, makefile, vidsupport.h) - no tests/, no
# check/test target in the makefile, no CI.  These cases therefore assert on
# documented CLI and data-path behaviour from a consumer's point of view.
#
# Runtime surface of the tool:
#   * /proc/profile needs CONFIG_PROFILING plus root;
#   * the "top"-style layout is just ANSI escape sequences written to stdout
#     (vidsupport.h) - it needs no controlling terminal, so the whole
#     compute/print path is reachable unprivileged by pointing -m/-p at
#     ordinary files.
# Everything below therefore runs WITHOUT root and WITHOUT a tty, and every
# case actually exec()s the packaged ELF: a broken OHOS .codesign would show
# up as rc=126 here instead of being hidden by a file-exists check.
#
# /tmp is read-only on OHOS and getcwd() is unreliable under the build-slot
# wrapper, so the scratch dir is derived from $0 (pure string handling) rather
# than from pwd.  KERNELTOP_TEST_TMPD overrides it for the caller's convenience.
set -u

BASE="${KERNELTOP_TEST_TMPD:-$(dirname "$0")}"
TMPD="$BASE/.kerneltop-test-$$"
mkdir -p "$TMPD" || exit 90
trap 'rm -rf "$TMPD"' EXIT

PASS=0
FAIL=0
TOTAL=0
ok()  { echo "PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }
one() { TOTAL=$((TOTAL+1)); }

# Strip ANSI CSI introducers so emitted rows are greppable as plain text.
deansi() { tr -d '\033'; }
# Emit "symbol->ticks" pairs in report order, single-space separated.
rows() {
    deansi | awk '{for (i = 1; i <= NF; i++)
                       if ($i ~ /^(func_|_stext|_etext)/)
                           printf "%s%s->%s", (n++ ? " " : ""), $i, $(i + 1)}
                 END {printf "\n"}'
}

# Synthetic System.map: _stext .. _etext with three text symbols.
cat > "$TMPD/map.txt" <<'EOF'
00001000 T _stext
00001000 t func_alpha
00001004 t func_beta
00001008 t func_gamma
00001010 T _etext
EOF

# Synthetic profiling buffer: u32 sampling_step = 4, then 4 tick buckets
# 1, 2, 3, 7.  With adr0 = 0x1000 and step 4 the buckets land on
# _stext(1), func_beta(2), func_gamma(3), and 0x100c resolves back to
# func_gamma(7) => func_gamma 10.  func_alpha stays at 0 ticks.  Total 13.
printf '\004\000\000\000\001\000\000\000\002\000\000\000\003\000\000\000\007\000\000\000' > "$TMPD/profile.bin"

echo "--- kerneltop 0.92 consumer test suite ---"

# 1. -V prints the version and exits 0 (proves the ELF really executes)
echo "[1] kerneltop -V"
if kerneltop -V </dev/null >"$TMPD/t1.out" 2>"$TMPD/t1.err"; then
    if grep -q "Version 0.92" "$TMPD/t1.out"; then
        ok "-V prints 'kerneltop Version 0.92' on stdout and exits 0"
    else
        bad "-V exited 0 but stdout lacks the version: $(cat "$TMPD/t1.out")"
    fi
else
    bad "-V should exit 0; stderr: $(cat "$TMPD/t1.err")"
fi
one

# 2. unknown option -> option table on stderr, non-zero exit
echo "[2] kerneltop -Z"
if kerneltop -Z </dev/null >"$TMPD/t2.out" 2>"$TMPD/t2.err"; then
    bad "-Z (unknown option) must not exit 0"
else
    if grep -q "usage:" "$TMPD/t2.err" && grep -q -- "-V  " "$TMPD/t2.err"; then
        ok "-Z prints the option table (incl. -V) on stderr and exits non-zero"
    else
        bad "-Z stderr has no usage block: $(head -3 "$TMPD/t2.err")"
    fi
fi
one

# 3. explicitly named missing map file -> no default fallback, exit non-zero
echo "[3] kerneltop -m <nonexistent>"
if kerneltop -m "$TMPD/absent.map" </dev/null >"$TMPD/t3.out" 2>"$TMPD/t3.err"; then
    bad "-m with an absent map file must exit non-zero"
else
    if grep -q "No such file or directory" "$TMPD/t3.err"; then
        ok "-m on an absent map file reports ENOENT and exits non-zero"
    else
        bad "-m absent-map stderr unexpected: $(cat "$TMPD/t3.err")"
    fi
fi
one

# 4. malformed map line rejected with its line number
echo "[4] kerneltop -m <malformed map>"
printf 'this is not a map line\n' > "$TMPD/badmap.txt"
if kerneltop -m "$TMPD/badmap.txt" </dev/null >"$TMPD/t4.out" 2>"$TMPD/t4.err"; then
    bad "malformed map line must exit non-zero"
else
    if grep -q "wrong map line" "$TMPD/t4.err"; then
        ok "malformed map line rejected ('wrong map line')"
    else
        bad "malformed map stderr unexpected: $(cat "$TMPD/t4.err")"
    fi
fi
one

# 5. map without _stext rejected
echo "[5] kerneltop -m <map without _stext>"
printf '00001000 T _text\n00002000 T _etext\n' > "$TMPD/nostext.txt"
if kerneltop -m "$TMPD/nostext.txt" </dev/null >"$TMPD/t5.out" 2>"$TMPD/t5.err"; then
    bad "map without _stext must exit non-zero"
else
    if grep -q "can't find '_stext'" "$TMPD/t5.err"; then
        ok "map without _stext rejected (\"can't find '_stext'\")"
    else
        bad "_stext-missing stderr unexpected: $(cat "$TMPD/t5.err")"
    fi
fi
one

# 6. descending address order inside the text range rejected
echo "[6] kerneltop -m <descending map>"
printf '00002000 T _stext\n00002004 t func_a\n00002002 t func_b\n00003000 T _etext\n' > "$TMPD/descmap.txt"
if kerneltop -m "$TMPD/descmap.txt" </dev/null >"$TMPD/t6.out" 2>"$TMPD/t6.err"; then
    bad "descending map must exit non-zero"
else
    if grep -q "descending address order in map line" "$TMPD/t6.err"; then
        ok "descending address order rejected"
    else
        bad "descending-map stderr unexpected: $(cat "$TMPD/t6.err")"
    fi
fi
one

# 7. full data path, sorted: ticks bucketed per symbol, emitted descending
echo "[7] kerneltop -m map -p profile (sorted pass)"
printf 'q' | timeout 20 kerneltop -m "$TMPD/map.txt" -p "$TMPD/profile.bin" -s 1 -l 20 -t 1 \
    >"$TMPD/t7.out" 2>"$TMPD/t7.err"
rc=$?
R7=$(rows <"$TMPD/t7.out")
if [ "$rc" -eq 0 ] \
   && deansi <"$TMPD/t7.out" | grep -q "Sampling_step: 4 | Address range: 0x1000 - 0x1010" \
   && deansi <"$TMPD/t7.out" | grep -q "(    13)" \
   && [ "$R7" = "func_gamma->10 func_beta->2 _stext->1" ]; then
    ok "sorted pass emits func_gamma=10, func_beta=2, _stext=1 (total 13), 0-tick func_alpha dropped"
else
    bad "sorted pass mismatch: rc=$rc rows='$R7' err=$(cat "$TMPD/t7.err")"
    deansi <"$TMPD/t7.out"
fi
one

# 8. differential check: -u skips the insertion sort -> table order
echo "[8] kerneltop -m map -p profile -u (unsorted pass)"
printf 'q' | timeout 20 kerneltop -m "$TMPD/map.txt" -p "$TMPD/profile.bin" -s 1 -u \
    >"$TMPD/t8.out" 2>"$TMPD/t8.err"
rc=$?
R8=$(rows <"$TMPD/t8.out")
if [ "$rc" -eq 0 ] && [ "$R8" = "_stext->1 func_beta->2 func_gamma->10" ]; then
    ok "-u emits the same ticks in table order, proving case 7 really sorted them"
else
    bad "-u order mismatch: rc=$rc rows='$R8'"
    deansi <"$TMPD/t8.out"
fi
one

# 9. -t threshold filters low-tick symbols out of the report
echo "[9] kerneltop -t 5 (threshold)"
printf 'q' | timeout 20 kerneltop -m "$TMPD/map.txt" -p "$TMPD/profile.bin" -s 1 -t 5 \
    >"$TMPD/t9.out" 2>"$TMPD/t9.err"
rc=$?
R9=$(rows <"$TMPD/t9.out")
if [ "$rc" -eq 0 ] && [ "$R9" = "func_gamma->10" ]; then
    ok "-t 5 keeps only func_gamma (10 ticks) and drops the 1- and 2-tick symbols"
else
    bad "-t 5 rows mismatch: rc=$rc rows='$R9'"
    deansi <"$TMPD/t9.out"
fi
one

# 10. valid map + absent profile reaches profile_read and prints the
#     profiling-disabled hint (documented unprivileged failure mode)
echo "[10] kerneltop -m map -p <nonexistent profile>"
if kerneltop -m "$TMPD/map.txt" -p "$TMPD/absent-profile.bin" </dev/null \
        >"$TMPD/t10.out" 2>"$TMPD/t10.err"; then
    bad "absent profile file must exit non-zero"
else
    if grep -q "enable kernel profiling \[profile=N\]" "$TMPD/t10.err"; then
        ok "reaches profile_read past a valid map and reports 'enable kernel profiling'"
    else
        bad "profile-missing stderr unexpected: $(cat "$TMPD/t10.err")"
    fi
fi
one

echo "--- results: $PASS/$TOTAL passed, $FAIL failed ---"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
