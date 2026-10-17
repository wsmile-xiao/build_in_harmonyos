#!/bin/sh
# test_bali_phy.sh - bali-phy consumer functional test
#
# usage: sh test_bali_phy.sh <path-to-bali-phy> <examples-dir>
#
# Exercises the ported binary end to end:
#   1) --version output (program name + version)
#   2) --help output
#   3) --test self-check ("Analyze the initial values and exit") on the
#      installed 5S rRNA example - also verifies the builtins shared
#      modules load (dlopen) at runtime
#   4) a short MCMC run (--iter=20) on the installed example

BP="$1"
EX="$2"
CHECKS=0
FAILED=0

check() {
    want="$1"
    desc="$2"
    CHECKS=$((CHECKS+1))
    if [ "$want" -ne 0 ]; then
        FAILED=$((FAILED+1))
        echo "FAIL: $desc"
    else
        echo "PASS: $desc"
    fi
}

if [ -z "$BP" ] || [ ! -f "$BP" ]; then
    echo "FAIL: bali-phy binary not found: $BP"
    exit 1
fi

# writable scratch dir: try $TMPDIR, fall back to the current directory
# (the test_package run folder); /tmp is read-only on HarmonyOS.
WORK="$(mktemp -d 2>/dev/null)"
if [ -z "$WORK" ] || [ ! -d "$WORK" ]; then
    WORK="$(pwd)/bali-phy-test-$$"
    mkdir -p "$WORK"
fi
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1

# --- 1. version ----------------------------------------------------------
"$BP" --version > version.out 2>&1
check $? "bali-phy --version exits 0"
grep -qi VERSION version.out
check $? "bali-phy --version prints VERSION line"
grep -qi "4.1" version.out
check $? "bali-phy --version prints version 4.1"

# --- 2. help -------------------------------------------------------------
"$BP" --help > help.out 2>&1
check $? "bali-phy --help exits 0"
grep -qi "options" help.out
check $? "bali-phy --help prints options"

# --- 3. --test self-check on the installed example -----------------------
FASTA="$EX/5S-rRNA/5d-muscle.fasta"
if [ -f "$FASTA" ]; then
    check 0 "installed example 5d-muscle.fasta exists"
    "$BP" "$FASTA" --test > test.out 2>&1
    check $? "bali-phy <5d> --test exits 0 (builtins load + initial analysis)"
    grep -qi "likelihood" test.out
    check $? "--test prints initial likelihood"
else
    check 1 "installed example 5d-muscle.fasta exists"
fi

# --- 4. short MCMC run ---------------------------------------------------
"$BP" "$FASTA" --iter=20 > iter.out 2>&1
check $? "bali-phy <5d> --iter=20 MCMC run exits 0"
grep -qi "^iter" 5d-muscle-1/C1.log && [ "$(wc -l < 5d-muscle-1/C1.log)" -ge 2 ]
check $? "MCMC log file contains likelihood samples"

echo "TOTAL: $CHECKS checks, $FAILED failed"
exit "$FAILED"
