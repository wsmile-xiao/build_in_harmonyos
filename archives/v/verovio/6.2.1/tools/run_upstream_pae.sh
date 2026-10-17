#!/bin/sh
# run_upstream_pae.sh
#
# Runs the verovio upstream test-suite inputs (doc/tests/pae/**/*.pae, 78 files)
# through the verovio CLI. The official suite (doc/test-suite.py) renders these
# same PAE inputs to SVG via the verovio Python/SWIG module + cairosvg; here we
# exercise the exact same 78 upstream inputs through the compiled CLI renderer,
# which is the subset needed on HarmonyOS (no Python SWIG module / cairosvg).
#
# Each case PASSes iff the CLI exits 0 AND the SVG produced on stdout is
# non-empty and has a <svg> root element. Counts come from the loop's own
# control flow (single deterministic source), not from parsing stdout, and are
# emitted as the HMBS_UPSTREAM_TEST_RESULT marker.
#
# Device note (round-13/14): on the HarmonyOS PC preflight sandbox the CLI's own
# file writes (std::ofstream -> <out>.svg) are not visible afterwards, even
# though the CLI prints "Output written to ..." and exits 0; files created by
# the shell (stderr redirects, files.list) ARE visible. The render result is
# therefore captured via the CLI's standard stdout output (-o -), which flows
# through the shell's pipe and is visible. This still runs the exact same
# PAE->SVG render pipeline for every upstream input and asserts a non-empty SVG
# with a <svg> root element - nothing is skipped or stubbed.
#
# NOTE: this script is intentionally POSIX-sh compatible. The HMBS harness runs
# it through $CONFIG_SHELL, which is /bin/sh on the HarmonyOS device, so no
# bash-only constructs (mapfile / process substitution / arrays / <<<) are
# allowed. The input list is materialised into a temp file so the counting loop
# stays in the current shell (a plain pipe would run it in a subshell and lose
# counters).
#
# Usage:
#   run_upstream_pae.sh <verovio-cli> <resource-dir> <tests-dir> [outdir]
set -u

CLI="$1"
RES="$2"
TESTS="$3"
OUTDIR="${4:-}"
[ -z "$OUTDIR" ] && OUTDIR="${TMPDIR:-/tmp}/verovio-upstream-$$"
mkdir -p "$OUTDIR"

# Pre-flight: the CLI must be runnable on the target. If it cannot even print
# its version, that is an infrastructure/environment problem and we must not
# turn it into "0 test failures" - fail loudly instead.
if ! "$CLI" --version >/dev/null 2>"$OUTDIR/version.err"; then
    echo "FATAL: verovio CLI not runnable on target (see $OUTDIR/version.err)" >&2
    exit 1
fi

# Collect all *.pae inputs in deterministic (sorted) order - the same inputs the
# official doc/test-suite.py iterates (ignore doc/tests/... json / non-pae).
# Materialise the list into a temp file (POSIX sh has no mapfile/arrays, and a
# pipe would lose the counters to the subshell).
LIST="$OUTDIR/files.list"
if ! find "$TESTS" -name '*.pae' | sort >"$LIST"; then
    echo "FATAL: could not enumerate test inputs under $TESTS" >&2
    exit 1
fi

TOTAL=0
PASS=0
FAIL=0
SKIP=0

while IFS= read -r f; do
    [ -n "$f" ] || continue
    TOTAL=$((TOTAL + 1))
    err="$OUTDIR/case_${TOTAL}.err"
    # Render the input to SVG on stdout (-o -); the CLI appends nothing and
    # prints the SVG document on stdout. stderr (warnings/errors) goes to a
    # shell-created file so failures carry concrete diagnostics.
    svg=$("$CLI" -f pae -r "$RES" -o - "$f" 2>"$err")
    rc=$?
    if [ $rc -ne 0 ]; then
        echo "FAIL(rc=$rc): ${f##*/}"
        if [ -s "$err" ]; then
            sed 's/^/    stderr: /' "$err" | tail -3
        fi
        FAIL=$((FAIL + 1))
    elif [ -z "$svg" ]; then
        echo "FAIL(empty): ${f##*/}"
        if [ -s "$err" ]; then
            sed 's/^/    stderr: /' "$err" | tail -3
        fi
        FAIL=$((FAIL + 1))
    else
        case "$svg" in
            *'<svg'*)
                echo "PASS: ${f##*/}"
                PASS=$((PASS + 1))
                ;;
            *)
                echo "FAIL(no-svg-root): ${f##*/}"
                FAIL=$((FAIL + 1))
                ;;
        esac
    fi
    rm -f "$err"
done < "$LIST"

EXECUTED=$((PASS + FAIL + SKIP))

if [ -z "${TOTAL:-}" ] || [ "$TOTAL" -le 0 ]; then
    # No upstream test inputs found at all - do not fabricate a pass.
    printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"cli_render_pae","command":"verovio -f pae -r <res> <test.pae>","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"no *.pae inputs found under %s"}\n' "$TESTS"
else
    status="passed"
    [ "$FAIL" -gt 0 ] && status="failed"
    printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"cli_render_pae","command":"verovio -f pae -r <res> <test.pae>","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}\n' \
        "$status" "$TOTAL" "$EXECUTED" "$PASS" "$FAIL" "$SKIP"
fi

echo "upstream PAE suite summary: discovered=$TOTAL executed=$EXECUTED passed=$PASS failed=$FAIL skipped=$SKIP"

# Always exit 0 so the build is not spuriously blocked; the marker carries the
# true result. (Only a non-runnable CLI aborts, above.)
exit 0
