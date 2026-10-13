#!/bin/sh
#--------------------------------------------------------------------
# Upstream test runner for skkdic 20230109.
#
# Executes upstream's own test suite -- the two Emacs ERT cases shipped in
# zipcode/test/zipcode-test.el of the 20230109 release tarball -- against the
# *installed* package, with the very command upstream's own test target uses
# (zipcode/Makefile.in:116-118):
#
#   $(EMACS) --batch --quick --directory test --load test/all-tests.el \
#             --funcall ert-run-tests-batch-and-exit
#
# The two cases read SKK-JISYO.zipcode / SKK-JISYO.office.zipcode from the
# current directory (coding-system-for-read 'euc-jp) and compare the whole
# entry line for postal codes 6020033 / 1008926 against the expected string,
# so the runner chdirs into the installed share/skk tree: the dictionaries
# under test are literally the ones the package ships.  No test code is
# vendored into the repository -- the conanfile fetches the release tarball
# itself and pins it by sha256.
#
# Env:
#   EMACS_BIN         installed `emacs` executable (emacs/29.1 OHOS package)
#   DATADIR           installed dictionary tree (<package_folder>/share/skk)
#   UPSTREAM_TESTDIR  directory holding all-tests.el + zipcode-test.el
#   EXPECTED_TESTS    number of upstream ERT cases (default 2)
#   TMPDIR            writable scratch root (OHOS /tmp is read-only)
# Exit: 0 = every upstream case executed and passed, non-zero = failure
#--------------------------------------------------------------------
set -u

EMACS_BIN="${EMACS_BIN:?EMACS_BIN must point to the emacs executable}"
DATADIR="${DATADIR:?DATADIR must point to the installed dictionary tree}"
UPSTREAM_TESTDIR="${UPSTREAM_TESTDIR:?UPSTREAM_TESTDIR must hold the upstream .el tests}"
EXPECTED_TESTS="${EXPECTED_TESTS:-2}"

checks=0
fails=0

ok() {
    checks=$((checks + 1))
    echo "PASS: $1"
}

bad() {
    checks=$((checks + 1))
    fails=$((fails + 1))
    echo "FAIL: $1"
}

summary() {
    echo "UPSTREAM_CHECK_SUMMARY tests=$EXPECTED_TESTS passed=${npassed:-0} checks=$checks fails=$fails"
}

npassed=0

# --- 1. harness: the runner and the fixtures must be where we expect them ---
[ -x "$EMACS_BIN" ] && ok "emacs executable present: $EMACS_BIN" \
                    || bad "emacs not executable: $EMACS_BIN"
[ -d "$DATADIR" ] && ok "installed dictionary tree present: $DATADIR" \
                  || bad "installed dictionary tree missing: $DATADIR"
[ -f "$DATADIR/SKK-JISYO.zipcode" ] \
    && ok "SKK-JISYO.zipcode installed (case 1 input)" \
    || bad "SKK-JISYO.zipcode missing from $DATADIR"
[ -f "$DATADIR/SKK-JISYO.office.zipcode" ] \
    && ok "SKK-JISYO.office.zipcode installed (case 2 input)" \
    || bad "SKK-JISYO.office.zipcode missing from $DATADIR"
[ -f "$UPSTREAM_TESTDIR/all-tests.el" ] \
    && ok "upstream entry point present: all-tests.el" \
    || bad "upstream entry point missing: $UPSTREAM_TESTDIR/all-tests.el"
[ -f "$UPSTREAM_TESTDIR/zipcode-test.el" ] \
    && ok "upstream case file present: zipcode-test.el" \
    || bad "upstream case file missing: $UPSTREAM_TESTDIR/zipcode-test.el"

# The emacs/29.1 package publishes its own runtime tree through conanrun; a
# batch run without EMACSLOADPATH cannot load its lisp and errors out before
# any case executes, which must never be mistaken for "the cases ran".
if [ -n "${EMACSLOADPATH:-}" ] && [ -d "${EMACSLOADPATH}" ]; then
    ok "EMACSLOADPATH points at a directory: ${EMACSLOADPATH}"
else
    bad "EMACSLOADPATH is not set to a directory (emacs cannot load its own lisp)"
fi

# The number of cases is a fact taken from upstream's own file, not a value
# asserted by hand: count ert-deftest in the file we are about to run.
if [ -f "$UPSTREAM_TESTDIR/zipcode-test.el" ]; then
    n_deftest=$(grep -c '(ert-deftest' "$UPSTREAM_TESTDIR/zipcode-test.el" || true)
    if [ "$n_deftest" -eq "$EXPECTED_TESTS" ]; then
        ok "upstream case count == $EXPECTED_TESTS (ert-deftest in zipcode-test.el)"
    else
        bad "expected $EXPECTED_TESTS upstream cases, zipcode-test.el declares $n_deftest"
    fi
else
    bad "cannot count upstream cases: zipcode-test.el missing"
fi

if [ "$fails" -ne 0 ]; then
    echo "FAIL: upstream fixtures incomplete, not running ERT"
    summary
    exit 1
fi

# --- 2. run upstream's own ERT batch entry point ---
SCRATCH="${TMPDIR:-$HOME/tmp}/skkdic-upstream-$$"
rm -rf "$SCRATCH"
if ! mkdir -p "$SCRATCH"; then
    echo "FAIL: cannot create scratch dir: $SCRATCH"
    summary
    exit 1
fi
OUT="$SCRATCH/ert.out"

# cwd = the installed dictionary tree: the cases read ./SKK-JISYO.*.zipcode
if ! cd "$DATADIR"; then
    echo "FAIL: cannot enter installed dictionary tree: $DATADIR"
    summary
    exit 1
fi

"$EMACS_BIN" --batch --quick \
    --directory "$UPSTREAM_TESTDIR" \
    --load "$UPSTREAM_TESTDIR/all-tests.el" \
    --funcall ert-run-tests-batch-and-exit > "$OUT" 2>&1
rc=$?

echo "--- upstream ERT output (emacs --batch ... ert-run-tests-batch-and-exit) ---"
cat "$OUT"
echo "--- end upstream ERT output ---"

[ "$rc" -eq 0 ] && ok "emacs ERT batch run exited 0 (rc=$rc)" \
                || bad "emacs ERT batch run exited $rc"

# --- 3. the reported numbers must match the upstream case count ---
ran=$(sed -n 's/^Ran \([0-9][0-9]*\) tests.*/\1/p' "$OUT" | tail -n 1)
if [ "${ran:-}" = "$EXPECTED_TESTS" ]; then
    ok "ERT reported 'Ran $EXPECTED_TESTS tests'"
else
    bad "ERT reported 'Ran ${ran:-none} tests', expected $EXPECTED_TESTS"
fi

unexpected=$(sed -n 's/.*, \([0-9][0-9]*\) unexpected.*/\1/p' "$OUT" | tail -n 1)
if [ "${unexpected:-}" = "0" ]; then
    ok "ERT summary reports 0 unexpected results"
else
    bad "ERT summary reports ${unexpected:-unknown} unexpected results"
fi

npassed=$(sed -n 's/^ *passed *[0-9][0-9]*\/[0-9][0-9]*.*/x/p' "$OUT" | wc -l | tr -d ' ')
if [ "$npassed" -eq "$EXPECTED_TESTS" ]; then
    ok "all $EXPECTED_TESTS upstream cases reported 'passed'"
else
    bad "$npassed of $EXPECTED_TESTS upstream cases reported 'passed'"
fi

# Per case verdict, printed by upstream's own runner.
for case_name in jisyo-zipcode/test1 jisyo-office-zipcode/test1; do
    if grep -qE "^ *passed +[0-9]+/[0-9]+ +${case_name}([ (]|$)" "$OUT"; then
        ok "upstream case $case_name passed"
    else
        bad "upstream case $case_name did not report 'passed'"
    fi
done

rm -rf "$SCRATCH"

summary
[ "$fails" -eq 0 ]
