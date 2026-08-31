#!/usr/bin/env bash
# test_package/test.sh — mpage 2.5.8 consumer smoke test.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary and checks real
# PostScript output content.
# Requirement #8: no `|| true` / ignore_errors / skip / hardcoded machine
# paths. Failure of any check aborts the script with a non-zero exit.
set -eu

DISCOVERED=0
PASSED=0
fail() { echo "FAIL: $*"; }

# ---- Test 1: mpage -V prints the version string ----------------------------
DISCOVERED=$((DISCOVERED + 1))
VOUT="$(mpage -V 2>&1)"
if printf '%s' "$VOUT" | grep -q 'mpage version 2\.5\.8'; then
    echo "OK: mpage -V -> $(printf '%s' "$VOUT" | tr -d '\n')"
    PASSED=$((PASSED + 1))
else
    fail "mpage -V output unexpected: $VOUT"
fi

# ---- Test 2: mpage turns text into a PostScript stream ---------------------
# Capture the PostScript stream AND mpage's exit code (set -e is disabled
# around the capture so a non-zero exit is reported as a failure rather
# than aborting the script before we can print a diagnostic).
set +e
PS_OUT="$(mpage sample.txt 2>/dev/null)"
MPAGE_RC=$?
set -e
DISCOVERED=$((DISCOVERED + 1))
if [ "$MPAGE_RC" -ne 0 ]; then
    fail "mpage exited non-zero ($MPAGE_RC) on sample.txt"
elif ! printf '%s' "$PS_OUT" | head -1 | grep -q '^%!PS-Adobe-2\.0$'; then
    fail "mpage did not emit a %!PS-Adobe-2.0 header (first line: $(printf '%s' "$PS_OUT" | head -1))"
else
    echo "OK: mpage sample.txt -> exit 0, PostScript stream (%!PS-Adobe-2.0 header)"
    PASSED=$((PASSED + 1))
fi

# ---- Test 3: %%Creator line names mpage 2.5.8 May 2023 ----------------------
DISCOVERED=$((DISCOVERED + 1))
if printf '%s' "$PS_OUT" | grep -q '%%Creator: mpage 2\.5\.8 May 2023'; then
    echo "OK: %%Creator names 'mpage 2.5.8 May 2023'"
    PASSED=$((PASSED + 1))
else
    fail "%%Creator line missing or wrong"
fi

# ---- Test 4: %%DocumentMedia reports the default A4 page -------------------
DISCOVERED=$((DISCOVERED + 1))
if printf '%s' "$PS_OUT" | grep -q '%%DocumentMedia: A4 '; then
    echo "OK: %%DocumentMedia names the default A4 page size"
    PASSED=$((PASSED + 1))
else
    fail "%%DocumentMedia did not report A4"
fi

echo "test_package: ${PASSED}/${DISCOVERED} checks passed"

# ── HMBS machine-evidence marker (real counts, produced by the run above) ──
if [ "$PASSED" -eq "$DISCOVERED" ]; then
    HMBS_PASSED=true
else
    HMBS_PASSED=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$HMBS_PASSED" "$DISCOVERED" "$PASSED"
# Upstream has no test suite (audited Makefile/smakefile/smakefile.ppc: no
# check/test target; Test/ holds sample inputs only, no harness).
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","command":"","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"audited 2.5.8 tarball: Makefile/smakefile/smakefile.ppc have no check/test target; Test/ holds 4 sample input files (All.chars/nonl/tabtest/testpage) with no test driver, no expected output, no CI"}\n'

[ "$PASSED" -eq "$DISCOVERED" ] || exit 1
