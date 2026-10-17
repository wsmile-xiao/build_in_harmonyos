#!/bin/sh
# ============================================================================
# lucy 1.20 — upstream official test suite, executed on OHOS by `conan create`.
#
# Upstream ships no `check` target.  `README.FIRST` §Testing defines the
# official procedure instead:
#
#     lucy -v PUC19 PUC19splice atie.seq atie.qul atie.2nd -debug lucy.info
#     diff lucy.debug lucy.info      (golden cleave report)
#
# and, for multi-CPU hosts:
#
#     ... the same command above with the additional option -x CPU_count.
#     You should ... obtain the same output from lucy with or without this
#     option.
#
# This script implements both as test cases and is invoked from build() so that
# a plain `conan create` runs the upstream suite (docs/TEST_QUALITY_SPEC §3).
#
#   T1 upstream-golden-abi      golden cleave report comparison (1582 records)
#   T2 upstream-threaded-parse  `-x N` output must equal the single-thread run
#
# Comparison of T1 is delegated to golden-compare.py, which enforces the
# documented invariant (README.FIRST FAQ #6) instead of a blanket diff, because
# abi.c resolves ambiguous bases with libc random() and musl != glibc there.
#
# FIXTURE GUARD — README.FIRST §Testing asks for `-debug lucy.info` on purpose:
# lucy's default debug file name IS `lucy.debug`, i.e. the shipped golden file,
# so a bare `-debug` overwrites the reference and would make the next run
# compare the file against itself.  The sha256 of every fixture is pinned below
# and verified before use, so a clobbered golden file is reported, not hidden.
#
# Usage: upstream-regression.sh [<source-dir>]
# Exit status: 0 = all cases pass, 1 = at least one case failed, 2 = setup error
# ============================================================================
set -u

SRC=${1:-.}
cd "$SRC" || { echo "FATAL: cannot enter source dir '$SRC'"; exit 2; }

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
[ -n "$PY" ] || { echo "FATAL: no python3/python on PATH (required by golden-compare.py)"; exit 2; }

LUCY=./lucy
[ -x "$LUCY" ] || { echo "FATAL: $LUCY was not built in $SRC"; exit 2; }

# Sha256 of the upstream 1.20 fixtures (see conandata.yml for the tarball hash).
GOLDEN_SHA=88080a34480619e4c3dae98dfffb264cf231e88427fefa9c71c327f8dd9c1803
ATIE2ND_SHA=21ac3c13f723b5fc8543825ed72f6e68e378f6e871fb946c23900a02d31d9032
PUC19_SHA=81890c2b850cadc64f6f70e27666c811e1007d1752c34b475051b4cba9f26907
PUC19SPLICE_SHA=12ae268ae7cd1df7ff235f79b57c9f4fbc8eada4d39945b7096967aac34a310e

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        "$PY" -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
    fi
}

TOTAL=0
PASS=0
FAIL=0

setup_error=0
check_fixture() {   # check_fixture <file> <expected-sha>
    if [ ! -f "$1" ]; then
        echo "FATAL: upstream fixture '$1' is missing from the source tree"
        setup_error=1
        return
    fi
    actual=$(sha256 "$1")
    if [ "$actual" != "$2" ]; then
        echo "FATAL: upstream fixture '$1' does not match the published 1.20 archive"
        echo "       expected sha256 $2"
        echo "       actual   sha256 $actual"
        setup_error=1
    fi
}

check_fixture lucy.debug  "$GOLDEN_SHA"
check_fixture atie.2nd    "$ATIE2ND_SHA"
check_fixture PUC19       "$PUC19_SHA"
check_fixture PUC19splice "$PUC19SPLICE_SHA"
[ "$setup_error" -eq 0 ] || exit 2

echo "upstream fixture integrity: lucy.debug / atie.2nd / PUC19 / PUC19splice OK"
"$LUCY" 2>&1 | sed -n '1,2p'

# ── T1: upstream golden cleave report (README.FIRST §Testing step 1) ─────────
TOTAL=$((TOTAL + 1))
echo ""
echo "--------------------------------------------------------------------------"
echo "CASE T1  upstream-golden-abi"
echo "\$ $LUCY -v PUC19 PUC19splice atie.seq atie.qul atie.2nd -debug lucy.info"
rm -f lucy.info lucy.seq lucy.qul
if "$LUCY" -v PUC19 PUC19splice atie.seq atie.qul atie.2nd -debug lucy.info \
        > t1-golden.log 2>&1; then
    sed -n '/Phase 7/,$p' t1-golden.log
    "$PY" "$SCRIPT_DIR/golden-compare.py" lucy.debug lucy.info atie.2nd
    t1_rc=$?
else
    t1_rc=1
    echo "lucy exited with an error; last 20 log lines:"
    tail -20 t1-golden.log
fi
if [ "$t1_rc" -eq 0 ]; then
    PASS=$((PASS + 1)); echo "CASE T1 RESULT=PASS"
else
    FAIL=$((FAIL + 1)); echo "CASE T1 RESULT=FAIL"
fi

# ── T2: threaded equivalence (README.FIRST §Testing, multi-CPU note) ─────────
TOTAL=$((TOTAL + 1))
echo ""
echo "--------------------------------------------------------------------------"
echo "CASE T2  upstream-threaded-parse"
echo "\$ $LUCY -x 4 -v ... -debug lucy_mt.info -output lucy_mt.seq lucy_mt.qul"
rm -f lucy_mt.info lucy_mt.seq lucy_mt.qul
if "$LUCY" -x 4 -v PUC19 PUC19splice atie.seq atie.qul atie.2nd \
        -debug lucy_mt.info -output lucy_mt.seq lucy_mt.qul > t2-threaded.log 2>&1; then
    t2_rc=0
    for pair in "lucy.info lucy_mt.info" "lucy.seq lucy_mt.seq" "lucy.qul lucy_mt.qul"; do
        set -- $pair
        if cmp -s "$1" "$2"; then
            echo "  identical  $1 == $2"
        else
            echo "  DIFFERENT  $1 != $2 (threaded run diverged)"
            t2_rc=1
        fi
    done
else
    t2_rc=1
    echo "threaded lucy exited with an error; last 20 log lines:"
    tail -20 t2-threaded.log
fi
if [ "$t2_rc" -eq 0 ]; then
    PASS=$((PASS + 1)); echo "CASE T2 RESULT=PASS"
else
    FAIL=$((FAIL + 1)); echo "CASE T2 RESULT=FAIL"
fi

echo ""
echo "=========================================================================="
echo "SUITE upstream-regression: total=$TOTAL pass=$PASS fail=$FAIL"
echo "  T1 upstream-golden-abi      : golden report vs lucy.debug (1582 records)"
echo "  T2 upstream-threaded-parse  : single-thread vs -x 4 byte equivalence"
echo "logs: t1-golden.log t2-threaded.log"
echo "=========================================================================="

[ "$FAIL" -eq 0 ] || exit 1
exit 0
