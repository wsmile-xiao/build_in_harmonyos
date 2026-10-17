#!/bin/sh
# test_mb.sh — mrbayes consumer functional test
#
# usage: sh test_mb.sh <path-to-mb>
#
# Exercises the ported binary end to end:
#   1) --version output (GNU long option, CI smoke-test compatibility)
#   2) NEXUS parsing + likelihood computation + full MCMC run in batch mode
#   3) sump posterior summary output (marginal likelihoods, tree length)
#   4) clean exit on stdin EOF (non-interactive safety, no hang)

MB="$1"
CHECKS=0
FAILED=0

check() {
    # $1: 0 = ok / non-zero = fail, $2: description
    CHECKS=$((CHECKS + 1))
    if [ "$1" -ne 0 ]; then
        FAILED=$((FAILED + 1))
        echo "FAIL: check ${CHECKS}: $2"
    else
        echo "PASS: check ${CHECKS}: $2"
    fi
}

if [ -z "$MB" ] || [ ! -f "$MB" ]; then
    echo "FAIL: mb binary not found: $MB"
    exit 1
fi

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT

# --- 1. version ------------------------------------------------------------
"$MB" --version > "$WORK/version.out" 2>&1
check $? "mb --version exits 0"
grep -q "MrBayes" "$WORK/version.out"
check $? "mb --version prints program name"
grep -q "Version:" "$WORK/version.out"
check $? "mb --version prints version line"

# --- 2. full batch analysis ------------------------------------------------
cat > "$WORK/test.nex" <<'NEXUS_EOF'
#NEXUS
begin data;
    dimensions ntax=4 nchar=20;
    format datatype=dna missing=? gap=-;
    matrix
        Taxon_A ACGTTGCAATGGCCTAAGTC
        Taxon_B ACGTTGCAATGGCCTAAGTT
        Taxon_C ACGTTACAATGGCCTAAGTC
        Taxon_D ACGTTACAATGGCCTAAGTT
    ;
end;

begin mrbayes;
    set autoclose=yes nowarn=yes;
    lset nst=1 rates=equal;
    mcmc ngen=1000 nruns=1 nchains=1 samplefreq=100 printfreq=500;
    sump;
end;
NEXUS_EOF

cd "$WORK"
"$MB" test.nex > run.out 2>&1
check $? "mb batch analysis exits 0 (quitonerror semantics)"
grep -q "Analysis completed" run.out
check $? "MCMC analysis completed (likelihood + sampling)"
grep -q "Tasks completed, exiting program" run.out
check $? "non-interactive mode exits after tasks"

# --- 3. posterior summary output -------------------------------------------
grep -q "Estimated marginal likelihoods" run.out
check $? "sump prints marginal likelihood summary"
grep -q "TL" run.out
check $? "sump prints tree length parameter (TL)"

# --- 4. stdin EOF safety ---------------------------------------------------
"$MB" < /dev/null > "$WORK/eof.out" 2>&1
check $? "mb exits cleanly on stdin EOF (no interactive hang)"

echo "TOTAL: ${CHECKS} checks, ${FAILED} failed"
exit "$FAILED"
