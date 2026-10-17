#!/bin/sh
# test_package/test_ts.sh — functional + HarmonyOS-specific tests for ts(1).
# Runs in the conanrun env (PATH includes the packaged bin/).
#
# Upstream outils 0.14 ships NO test suite (no test/check/regress target in
# any of the 13 Makefiles, no tests/ directory, no CI config); the ts
# component only has ts.c + ts.1.  These binary-level assertions supplement
# that gap — client-side expectations follow the upstream ts(1) manual
# (SYNOPSIS/EXAMPLES) and were captured from the real packaged binary on
# this OHOS host before being written in (no guessed values).
#
# The last two groups are HarmonyOS-specific:
#   * T9 exercises the reallocarray(3) growth path of ts — exactly the code
#     path the OHOS portability patch exists for (OHOS musl libc has no
#     reallocarray(3)).
#   * T10 verifies the packaged ELF itself: AArch64 PIE, musl interpreter,
#     sole NEEDED entry libc.so, no RPATH/RUNPATH.
set -u

TMPD="$(pwd)"   # the test build dir is writable; /tmp is read-only on OHOS
PASS=0
FAIL=0

ok()   { echo "ok - $1"; PASS=$((PASS+1)); }
fail() { echo "FAIL - $1"; FAIL=$((FAIL+1)); }

check_eq() {   # name expected actual
    if [ "$3" = "$2" ]; then
        ok "$1"
    else
        fail "$1 (expected: [$2], got: [$3])"
    fi
}

echo "--- outils-ts 0.14 test suite (upstream automated tests: 0; assertions adapted) ---"

TS_BIN=$(command -v ts 2>/dev/null || true)
if [ -z "$TS_BIN" ]; then
    echo "FAIL - ts not found on PATH (conanrun env)"
    exit 1
fi
ok "ts binary found on PATH: $TS_BIN"

# --- T1: default format '%b %d %H:%M:%S' (man SYNOPSIS default) -----------
echo "[test] T1 default format: one timestamp per input line"
out=$(printf 'foo\nbar\n' | ts)
n=$(printf '%s\n' "$out" | grep -cE '^[A-Z][a-z]{2} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} (foo|bar)$')
check_eq "T1 two lines, each prefixed with '%b %d %H:%M:%S'" "2" "$n"

# --- T2: -i interval since previous line ----------------------------------
echo "[test] T2 -i: interval since the last timestamp"
out=$(printf 'a\nb\n' | ts -i)
n=$(printf '%s\n' "$out" | grep -cE '^[0-9]{2}:[0-9]{2}:[0-9]{2} [ab]$')
check_eq "T2 -i uses the %H:%M:%S default format" "2" "$n"

# --- T3: -s elapsed since program start -----------------------------------
echo "[test] T3 -s: elapsed time since program start"
out=$(printf 'a\nb\n' | ts -s)
n=$(printf '%s\n' "$out" | grep -cE '^[0-9]{2}:[0-9]{2}:[0-9]{2} [ab]$')
check_eq "T3 -s uses the %H:%M:%S default format" "2" "$n"

# --- T4: -m monotonic clock -----------------------------------------------
echo "[test] T4 -m: timestamps from a monotonic clock"
out=$(printf 'a\nb\n' | ts -m)
n=$(printf '%s\n' "$out" | grep -cE '^[A-Z][a-z]{2} [0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} [ab]$')
check_eq "T4 -m keeps the '%b %d %H:%M:%S' default format" "2" "$n"

# --- T5: user supplied strftime format ------------------------------------
echo "[test] T5 custom format operand"
out=$(printf 'x\n' | ts '%Y-%m-%d')
n=$(printf '%s\n' "$out" | grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2} x$')
check_eq "T5 format operand '%Y-%m-%d' is honoured" "1" "$n"

# --- T6: %.S microsecond extension (upstream EXAMPLES #2) ------------------
echo "[test] T6 microsecond extension %.S (upstream EXAMPLES: ls | ts -i %.S)"
out=$(printf 'CVS\nMakefile\nts.1\nts.c\n' | ts -i '%.S')
n=$(printf '%s\n' "$out" | grep -cE '^[0-9]{2}\.[0-9]{6} (CVS|Makefile|ts\.1|ts\.c)$')
check_eq "T6 %.S renders SS.microseconds" "4" "$n"

# --- T7: -i and -s are mutually exclusive (usage, exit 1) -----------------
echo "[test] T7 -i with -s is a usage error"
printf '' | ts -i -s >"$TMPD/t7.out" 2>"$TMPD/t7.err"
check_eq "T7 exit status" "1" "$?"
if grep -q '^usage: ts \[-i | -s\] \[-m\] \[format\]$' "$TMPD/t7.err"; then
    ok "T7 usage line on stderr"
else
    fail "T7 expected usage line on stderr"
fi
if [ -s "$TMPD/t7.out" ]; then
    fail "T7 must print nothing to stdout"
else
    ok "T7 prints nothing to stdout"
fi

# --- T8: more than one operand is a usage error ---------------------------
echo "[test] T8 extra operand is a usage error"
printf '' | ts a b >"$TMPD/t8.out" 2>"$TMPD/t8.err"
check_eq "T8 exit status" "1" "$?"
grep -q '^usage: ts ' "$TMPD/t8.err" && ok "T8 usage line on stderr" || fail "T8 expected usage line on stderr"

# --- T9: HarmonyOS-specific — reallocarray(3) growth path -----------------
# The ts.o object references reallocarray(3) (ts.c:204, in fmtprint() when
# strftime() does not fit the buffer).  OHOS musl libc has no reallocarray,
# which is why patches/0001 links the in-tree compat object.  A format
# operand that expands far beyond the initial buffer forces that call, so
# this case validates the OHOS portability fix rather than merely the UI.
echo "[test] T9 [OHOS] reallocarray(3) growth path (object added by patches/0001)"
out=$(printf 'x\n' | ts '%2000Y')
len=$(printf '%s' "$out" | wc -c | tr -d ' ')
if [ "$len" -gt 2000 ]; then
    ok "T9 dynamic growth path works: output is $len chars (> 2000)"
else
    fail "T9 expected >2000 chars from %2000Y, got $len"
fi
case "$out" in
    *' x') ok "T9 input line is preserved after the grown timestamp" ;;
    *)     fail "T9 input line missing after the grown timestamp" ;;
esac

# --- T10: HarmonyOS-specific — packaged ELF ABI/loader/deps --------------
echo "[test] T10 [OHOS] packaged ELF is an AArch64 PIE for OHOS musl"
set -- $(od -An -tx1 -N20 "$TS_BIN")
check_eq "T10 ELF magic (7f 45 4c 46)" "7f454c46" "$1$2$3$4"
check_eq "T10 EI_CLASS = ELFCLASS64" "02" "$5"
check_eq "T10 EI_DATA = little-endian" "01" "$6"
# NB: mksh parses $17 as ${1}7, so multi-digit positional params need braces.
check_eq "T10 e_type = ET_DYN (PIE)" "0300" "${17}${18}"
check_eq "T10 e_machine = EM_AARCH64 (183)" "b700" "${19}${20}"

n_needed=$(readelf -d "$TS_BIN" 2>/dev/null | grep -c '(NEEDED)')
check_eq "T10 exactly one NEEDED entry" "1" "$n_needed"
if readelf -d "$TS_BIN" 2>/dev/null | grep '(NEEDED)' | grep -q '\[libc\.so\]'; then
    ok "T10 sole dependency is libc.so (musl libc)"
else
    fail "T10 expected sole dependency [libc.so]"
fi
if readelf -p .interp "$TS_BIN" 2>/dev/null | grep -q 'ld-musl-aarch64'; then
    ok "T10 interpreter is the OHOS musl aarch64 dynamic linker"
else
    fail "T10 expected /lib/ld-musl-aarch64.so.1 interpreter"
fi
n_rpath=$(readelf -d "$TS_BIN" 2>/dev/null | grep -ciE '(RPATH|RUNPATH)')
check_eq "T10 no RPATH/RUNPATH entries" "0" "$n_rpath"

rm -f "$TMPD/t7.out" "$TMPD/t7.err" "$TMPD/t8.out" "$TMPD/t8.err"

echo "--- results: $PASS passed, $FAIL failed ---"
if [ "$FAIL" -ne 0 ]; then
    echo "OUTILS_TS_TEST_FAILED"
    exit 1
fi
echo "OUTILS_TS_OK: all $PASS checks passed"
