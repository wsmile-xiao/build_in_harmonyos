#!/bin/sh
# Faithful re-run of upstream tests/complexity.test against the installed
# `complexity` binary (cache-hit survival).
#
# Authoritative upstream execution stays in the main recipe build()
# (`make check SUBDIRS=tests`, automake harness, TESTS=complexity.test).
# Problem: `conan create` skips build() entirely when the package binary is
# already in cache, so a re-run preflight on unchanged code emits no
# HMBS_UPSTREAM_TEST_RESULT and the evidence gate reports `incomplete`
# (observed 2026-09-08: "Already installed! (1 of 1)", test_package 2/2
# passed, upstream discovered=0). This script vendors the deterministic
# part of tests/complexity.test verbatim (same sedcmd, same expected table,
# same upstream_sample.c bytes as tests/sample.c) and runs it against the
# installed binary from test_package, so every preflight — rebuild or cache
# hit — carries real upstream evidence. No assertion is weakened: a stub
# binary (empty output) fails the title check and the cmp below.
# Difference vs build-tree run: phase 1 runs on upstream_sample.c instead
# of src/*.c, so the `handle_noop == 0` row check (needs the full src tree)
# stays exclusive to `make check`; both `Complexity Scores`/`Complexity
# Histogram` titles are still asserted here.
# Usage: test_upstream_check.sh <path-to-complexity>
set -u

BIN="${1:?usage: test_upstream_check.sh <path-to-complexity>}"
HERE="$(dirname "$0")"
SAMPLE="$HERE/upstream_sample.c"
WORKDIR="${TMPDIR:-${TMP:-${TEMP:-.}}}"
OUTFILE="$WORKDIR/upstream_complexity.out"
SAMPLFILE="$WORKDIR/upstream_complexity.samp"
RCFILE="$WORKDIR/upstream_complexity.rc"

if [ ! -f "$SAMPLE" ]; then
    echo "FAIL: vendored sample missing: $SAMPLE"
    exit 1
fi
if [ ! -s "$SAMPLE" ]; then
    echo "FAIL: vendored sample is empty (fixture not extracted?)"
    exit 1
fi

# Phase 1 (mirrors complexity.test part 1): rcfile-driven full scoring must
# print both titles.
printf 'hist\nscore\nthresh 0\n' > "$RCFILE"
phase1_out="$("$BIN" -I main "-<" "$RCFILE" "$SAMPLE" 2>&1)"
phase1_rc=$?
titles=0
if printf '%s' "$phase1_out" | grep -q '^Complexity Scores$'; then
    if printf '%s' "$phase1_out" | grep -q '^Complexity Histogram$'; then
        titles=2
    fi
fi
if [ "$phase1_rc" -ne 0 ] || [ "$titles" -ne 2 ]; then
    echo "FAIL: title check rc=$phase1_rc titles=$titles output=$phase1_out"
    rm -f "$RCFILE"
    exit 1
fi
echo "PASS: both Complexity titles present"
# NOTE: keep RCFILE for Phase 2 (upstream $cpx carries `-< rcfile` in BOTH
# phases; the rcfile enables hist+score display, without which the
# histogram/percentile rows are absent and cmp fails on those lines).

# Phase 2 (mirrors complexity.test part 2 verbatim): -t0 scoring piped
# through the identical sedcmd, cmp against the identical expected table.
# NOTE: upstream sedcmd only normalizes paths containing "tests/"
# (s@ [^ ]*tests/@ @). The build-tree run passes tests/sample.c so the
# absolute prefix collapses to " sample.c(...)". A TMPDIR absolute path
# without "tests/" would survive sed and mismatch at char 25, line 1
# (observed preflight). Hence copy the vendored bytes to $WORKDIR/tests/
# sample.c (same basename as upstream) and score that path, keeping the
# sedcmd and expected table byte-identical to upstream.
# Verified against https://git.savannah.gnu.org/cgit/complexity.git/plain/tests/complexity.test:
# samples=`ls s*mple.c`, cpx="complexity -< rcfile", phase2 is `$cpx -t0 $samples`.
sedcmd='/^[A-Z]/d;/^$/d;/^Highest score:/d;s@ [^ ]*tests/@ @'
TESTSDIR="$WORKDIR/tests"
mkdir -p "$TESTSDIR"
cp -f "$SAMPLE" "$TESTSDIR/sample.c"
# Line-ending hardening (new strategy vs path fix): the vendored sample is
# authored with LF, but a CRLF checkout would add one extra byte per line,
# shifting complexity's non-comment line counts and histogram/percentile
# rows while leaving per-procedure scores unchanged (observed: 5 scored
# rows match, histogram/percentile rows differ). Strip CR so scoring sees
# canonical LF bytes; a stub binary still fails the title/cmp checks below.
if command -v tr >/dev/null 2>&1; then
    tr -d '\r' < "$TESTSDIR/sample.c" > "$TESTSDIR/sample.c.lf" && mv -f "$TESTSDIR/sample.c.lf" "$TESTSDIR/sample.c"
fi
SCORED="$TESTSDIR/sample.c"
"$BIN" "-<" "$RCFILE" -t0 "$SCORED" 2>&1 | sed "$sedcmd" > "$OUTFILE"
if [ ! -s "$OUTFILE" ]; then
    echo "FAIL: scored output empty after sed (stub binary?)"
    rm -f "$OUTFILE" "$RCFILE"
    exit 1
fi
if grep -s -E '^error on ' "$OUTFILE"; then
    echo "FAIL: 'error on' found in scored output"
    rm -f "$OUTFILE" "$RCFILE"
    exit 1
fi
sed "$sedcmd" > "$SAMPLFILE" <<'_EOF_'
Complexity Scores
Score | ln-ct | nc-lns| file-name(line): proc-name
    0       1       1   .../tests/sample.c(1): oneline
    0       1       1   .../tests/sample.c(15): tst
    1       1       1   .../tests/sample.c(3): continuesameline
    1       2       2   .../tests/sample.c(20): test
    1       4       3   .../tests/sample.c(7): derefloop

Complexity Histogram
Score-Range  Lin-Ct
    0-9           8 ************************************************************

Scored procedure ct:        5
Non-comment line ct:        8
Average line score:         1
25%-ile score:              0 (75% in higher score procs)
50%-ile score:              1 (half in higher score procs)
75%-ile score:              1 (25% in higher score procs)
Highest score:              1 (continuesameline() in /.../sample.c)
_EOF_
if cmp "$OUTFILE" "$SAMPLFILE"; then
    echo "PASS: upstream sample scoring matches expected table"
    rm -f "$OUTFILE" "$SAMPLFILE" "$TESTSDIR/sample.c" "$RCFILE"
    exit 0
else
    echo "FAIL: scored output differs from upstream expected table"
    echo "--- OUTFILE (first 20 lines) ---"
    head -n 20 "$OUTFILE" 2>/dev/null || true
    echo "--- SAMPLFILE (first 20 lines) ---"
    head -n 20 "$SAMPLFILE" 2>/dev/null || true
    diff "$OUTFILE" "$SAMPLFILE" 2>&1 | head -n 20 || true
    rm -f "$OUTFILE" "$SAMPLFILE" "$TESTSDIR/sample.c" "$RCFILE"
    exit 1
fi
