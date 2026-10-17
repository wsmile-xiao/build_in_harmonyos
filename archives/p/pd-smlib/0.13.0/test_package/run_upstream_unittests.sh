#!/bin/sh
#--------------------------------------------------------------------
# Upstream test runner for pd-smlib 0.13.0.
#
# Executes the 37 unit tests that ship in the upstream release tarball
# (unittests/<class>-unittest.pd) against the *installed* package, using the
# very framework those patches instantiate: [testtools/unit-test-frame] from
# pd-testtools 0.1.
#
# The frame reads the reference render (<name>.wav) that sits next to the
# patch, drives the object under test through the patch's own inlet wiring and
# prints one result line per test to stdout:
#     STDDEV-ZERO 0 <name>      bit exact match          -> pass
#     STDDEV-SMALL <x> <name>   rms error < 1e-05        -> pass
#     STDDEV-LARGE <x> <name>   rms error >= 1e-05       -> FAIL
# so no extra assertion logic of ours decides the outcome: the comparison is
# upstream's own, against upstream's own reference renders.
#
# The patches are loaded as subpatches of one canvas (each keeps its own $0
# id space) so a single headless `pd` runs all 37.  A [delay] in the same
# canvas asks Pd to quit by itself once they have all run: relying on a
# SIGTERM instead would truncate Pd's block buffered stdout and silently drop
# the last results.
#
# Env:
#   PD_BIN         installed `pd` executable
#   EXT_DIR        directory holding the installed *.pd_linux externals
#   SMLIB_SRC      recipe source folder (holds unittests/ and the references)
#   TESTTOOLS_DIR  directory holding unit-test-frame.pd (+ meta patch)
#   QUIT_MS        Pd-side quit delay in ms (default 15000)
# Exit: 0 = all upstream tests executed and matched, 1 = failure
#--------------------------------------------------------------------
set -eu

PD_BIN="${PD_BIN:?PD_BIN must point to pd}"
EXT_DIR="${EXT_DIR:?EXT_DIR must point to the externals dir}"
SMLIB_SRC="${SMLIB_SRC:?SMLIB_SRC must point to the recipe source folder}"
TESTTOOLS_DIR="${TESTTOOLS_DIR:?TESTTOOLS_DIR must hold unit-test-frame.pd}"
QUIT_MS="${QUIT_MS:-15000}"

UNITTESTS="$SMLIB_SRC/unittests"
[ -x "$PD_BIN" ] || { echo "FAIL: pd not executable: $PD_BIN"; exit 1; }
[ -d "$EXT_DIR" ] || { echo "FAIL: externals dir missing: $EXT_DIR"; exit 1; }
[ -d "$UNITTESTS" ] || { echo "FAIL: upstream unittests dir missing: $UNITTESTS"; exit 1; }
[ -f "$TESTTOOLS_DIR/unit-test-frame.pd" ] || {
    echo "FAIL: upstream unit-test framework missing: $TESTTOOLS_DIR/unit-test-frame.pd"
    exit 1
}

# --- local emulation only: the WSL/qemu guest libc predates the glibc fortify
# shims that Pd references (__fd_chk).  Preload the prepared shim for the pd
# process when it exists; on a native OHOS runner (CI) the path is absent and
# pd is invoked directly.
FDCHK_SHIM=/opt/ohos-guest/lib/libfdchkshim.so
run_pd() {
    if [ -f "$FDCHK_SHIM" ]; then
        LD_PRELOAD="$FDCHK_SHIM" "$@"
    else
        "$@"
    fi
}

WORK="${TMPDIR:-.}/pd-smlib-upstream.$$"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT

# 1. the upstream test patches + their reference renders, byte for byte
cp "$UNITTESTS"/*.pd "$UNITTESTS"/*.wav "$WORK"/
rm -f "$WORK"/all-upstream-unittests.pd

# 2. the upstream unit-test framework, as the `testtools` Pd library the
#    patches ask for (the frame falls back to a patch-relative reference path
#    when ggee/getdir is absent, so ggee is not required).
mkdir -p "$WORK/testtools"
cp "$TESTTOOLS_DIR"/*.pd "$WORK/testtools/"

# 3. the installed externals under the `smlib/` namespace the patches use.
#    pd-lib-builder installs to <externals-root>/<libname>/, which is how Pd
#    resolves `smlib/<class>`; copy rather than symlink so the runner also
#    works on filesystems without symlink support.
mkdir -p "$WORK/smlib"
cp "$EXT_DIR"/*.pd_linux "$WORK/smlib/"

# 4. one canvas holding all 37 patches as subpatches + the self-quit
{
    echo '#N canvas 0 0 900 700 10;'
    echo '#X obj 20 20 loadbang;'
    echo "#X obj 20 60 delay $QUIT_MS;"
    echo '#X msg 20 100 \; pd quit;'
    echo '#X connect 0 0 1 0;'
    echo '#X connect 1 0 2 0;'
    for patch in "$WORK"/*-unittest.pd; do
        name=$(basename "$patch" .pd)
        head -n 1 "$patch"
        tail -n +2 "$patch"
        echo "#X restore 0 0 pd $name;"
    done
} > "$WORK/all-upstream-unittests.pd"

n_patches=$(ls "$WORK"/*-unittest.pd | wc -l | tr -d ' ')
n_refs=$(ls "$WORK"/*.wav | wc -l | tr -d ' ')
if [ "$n_patches" -ne "$n_refs" ]; then
    echo "FAIL: $n_patches upstream test patches but $n_refs reference renders"
    exit 1
fi

OUT="$WORK/pd.out"
ERR="$WORK/pd.err"
if command -v timeout >/dev/null 2>&1; then
    run_pd timeout 180 "$PD_BIN" -nogui -nosound -path "$WORK" \
        -open "$WORK/all-upstream-unittests.pd" > "$OUT" 2> "$ERR" || true
else
    run_pd "$PD_BIN" -nogui -nosound -path "$WORK" \
        -open "$WORK/all-upstream-unittests.pd" > "$OUT" 2> "$ERR" || true
fi

echo "--- upstream unit-test output ---"
cat "$OUT"
echo "--- end upstream unit-test output ---"

fails=0

# Every object under test must have been instantiated from the installed
# package.  A class that failed to load logs "<name> ..." + "... couldn't
# create" on two separate lines and leaves the frame with no data at all,
# which upstream's own comparison reports as STDDEV-ZERO -- i.e. a *silent
# pass*.  Pd only logs the "<name>" half when creation fails, so a non-zero
# count here is the only thing standing between a missing class and a green
# run.
missing=$(grep -c 'verbose(0): smlib/' "$ERR" || true)
if [ "$missing" -ne 0 ]; then
    echo "FAIL: $missing smlib object(s) failed to load from the installed package"
    grep -A1 'verbose(0): smlib/' "$ERR" || true
    fails=$((fails + 1))
else
    echo "PASS: all smlib objects under test loaded from the installed package"
fi

# A missing reference render makes the frame report an error instead of a
# stddev; that must never be counted as a pass.
refmiss=$(grep -c 'REFERENCE-FILE-ERROR' "$ERR" "$OUT" 2>/dev/null | grep -v ':0$' | wc -l | tr -d ' ' || true)
if [ "${refmiss:-0}" -ne 0 ]; then
    echo "FAIL: reference render(s) missing:"
    grep 'REFERENCE-FILE-ERROR' "$ERR" "$OUT" 2>/dev/null | grep -v '^Binary' || true
    fails=$((fails + 1))
else
    echo "PASS: every upstream test found its reference render"
fi

# Per test verdict, taken verbatim from upstream's own comparison.
: > "$WORK/verdicts"
for ref in "$WORK"/*.wav; do
    name=$(basename "$ref" .wav)
    verdict=$(sed 's/;$//' "$OUT" | awk -v n="$name" '$NF == n {print $1; exit}')
    if [ -z "$verdict" ]; then
        echo "FAIL: upstream test '$name' produced no result"
        fails=$((fails + 1))
    elif [ "$verdict" = "STDDEV-ZERO" ] || [ "$verdict" = "STDDEV-SMALL" ]; then
        echo "PASS: upstream test '$name' matched its reference render ($verdict)"
    else
        echo "FAIL: upstream test '$name' diverged from its reference render ($verdict)"
        fails=$((fails + 1))
    fi
    echo "$name $verdict" >> "$WORK/verdicts"
done

n_results=$(sed 's/;$//' "$OUT" | grep -c '^STDDEV-' || true)
if [ "$n_results" -ne "$n_refs" ]; then
    echo "FAIL: expected $n_refs upstream results, got $n_results"
    fails=$((fails + 1))
fi

echo "UPSTREAM_CHECK_SUMMARY tests=$n_refs results=$n_results fails=$fails"
sed 's/^/  /' "$WORK/verdicts"
[ "$fails" -eq 0 ]