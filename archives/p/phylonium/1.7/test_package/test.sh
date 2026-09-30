#!/bin/sh
# phylonium 1.7 consumer test (test_package).
#
# phylonium is an *application* (`bin_PROGRAMS = phylonium` in
# src/Makefile.am), so per R34 / AGENTS  §10.1 the consumer test must really
# execute the delivered binary and assert on its behaviour. Only printing, only
# linking or only checking that files exist would be rejected (and is exactly
# what the CI L1e reverse check hunts).
#
# Every expectation below is derived from the upstream source, not from a log:
#  - src/io.cxx just_print(): stdout is a PHYLIP distance matrix - line 1 is
#    the taxon count, then one row "<id> d1 .. dN" per input file.
#  - src/io.cxx extract_genome(): the row id is the file basename with a known
#    .fasta/.fa/.fas extension stripped.
#  - man/phylonium.1.in: "A distance of zero means that two sequences are
#    identical"; entries are Jukes-Cantor corrected and "nan" appears when the
#    input is shorter than 200 bp or too diverse (K > 0.5).
#  - src/phylonium.cxx version(): prints "phylonium " VERSION.
#  - src/io.cxx read_fasta(): open() failure calls err() -> exits EXIT_FAILURE.
#  - src/phylonium.cxx main(): fewer than 2 files -> usage(EXIT_FAILURE).
#  - std::mt19937 prng is consumed only by evo_model::bootstrap(), i.e. only
#    with --bootstrap, so a plain run is deterministic.
#
# The <200 bp "nan" rule is why the fixtures are 2000 bp long.
set -eu

BIN="${PHYLONIUM_BIN:-phylonium}"
W="${PWD}/phylonium-consumer-work"
rm -rf "$W"
mkdir -p "$W"
cd "$W"

pass=0
fail=0
ok() {
    pass=$((pass + 1))
    echo "ok   - $1"
}
no() {
    fail=$((fail + 1))
    echo "NOT OK - $1"
}

# ---------------------------------------------------------------------------
# Fixtures. Pure index arithmetic (all intermediates < 2^53) so the sequences
# are byte-reproducible; genomeB repeats genomeA's content under a different
# file name, genomeC substitutes every 40th base (50/2000 = 2.5% divergence).
# ---------------------------------------------------------------------------
genome() {  # $1 = output file, $2 = 1 to mutate every 40th base
    awk -v mut="$2" -v name="$1" 'BEGIN {
        n = 2000
        printf ">%s contig\n", name
        for (i = 0; i < n; i++) {
            k = (i * 13 + (i % 5) * 3 + int(i / 7)) % 4
            if (mut == 1 && i % 40 == 0) k = (k + 1) % 4
            printf "%s", substr("ACGT", k + 1, 1)
            if ((i + 1) % 60 == 0) printf "\n"
        }
        printf "\n"
    }' > "$1"
}
genome genomeA.fasta 0
genome genomeB.fasta 0
genome genomeC.fasta 1

# ---------------------------------------------------------------------------
# 1. --version really executes the delivered ELF and reports the right version
# ---------------------------------------------------------------------------
if "$BIN" --version > version.out 2>&1; then
    if grep -q '^phylonium 1\.7' version.out; then
        ok "--version runs on device and reports 'phylonium 1.7'"
    else
        no "--version ran but printed unexpected text: $(head -1 version.out)"
    fi
else
    rc=$?
    no "--version failed (rc=$rc); unsigned-ELF / loader rejection lands here"
    cat version.out || true
fi

# ---------------------------------------------------------------------------
# 2. main path: a 3-genome run must succeed and emit a matrix
# ---------------------------------------------------------------------------
if "$BIN" --progress=never genomeA.fasta genomeB.fasta genomeC.fasta > m1.out 2> m1.err; then
    ok "deduction run over 3 FASTA files exits 0"
else
    rc=$?
    no "deduction run failed (rc=$rc)"
    sed -n '1,15p' m1.err || true
fi

if [ -s m1.out ]; then
    ok "matrix on stdout is non-empty"
else
    no "stdout matrix is empty (all output would have gone to stderr)"
    sed -n '1,15p' m1.err || true
fi

# ---------------------------------------------------------------------------
# 3. PHYLIP contract: taxon count line + one row per input file, ids are the
#    stripped basenames in command-line order
# ---------------------------------------------------------------------------
if [ "$(head -1 m1.out | tr -d '[:space:]')" = "3" ]; then
    ok "first matrix line is the taxon count 3"
else
    no "first line is not the taxon count: '$(head -1 m1.out)'"
fi

ids=$(awk 'NR>1 { printf "%s ", $1 }' m1.out)
nrows=$(awk 'END { print NR - 1 }' m1.out)
if [ "$ids" = "genomeA genomeB genomeC " ] && [ "$nrows" = "3" ]; then
    ok "rows carry the 3 stripped FASTA basenames, no extra rows"
else
    no "row ids / row count wrong: ids='$ids' rows=$nrows"
fi

# ---------------------------------------------------------------------------
# 4. diagonal is exactly zero (self distance), i.e. real numbers were parsed
# For data row j (file line NR = j + 1) the self distance sits in field j + 1,
# i.e. exactly $NR - so a matrix that is really N x N must have $NR == 0.
# ---------------------------------------------------------------------------
if awk 'NR>1 { if ($NR + 0 != 0) { print "row " (NR - 1) " diagonal $" NR " = " $NR; exit 1 } }' m1.out > diag.err 2>&1; then
    ok "distance matrix diagonal is 0.0 for every genome"
else
    no "diagonal not zero: $(cat diag.err)"
fi

# ---------------------------------------------------------------------------
# 5. identical genomes -> distance 0 (documented semantics, not a smoke test)
# ---------------------------------------------------------------------------
dAB=$(awk 'NR==2 { print $3 }' m1.out)   # row A, column B
if [ "$dAB" = "0.0000e+00" ]; then
    ok "identical genomes A/B yield distance 0.0000e+00"
else
    no "A/B distance is not exactly zero (got '$dAB')"
fi

# ---------------------------------------------------------------------------
# 6. diverged genomes -> a finite, positive JC distance well inside the method
#    range (<0.5), i.e. the estimator actually computed something
# ---------------------------------------------------------------------------
dAC=$(awk 'NR==2 { print $4 }' m1.out)
if awk -v d="$dAC" 'BEGIN { if (d ~ /^[-+0-9.eE+-]+$/ && d + 0 > 0 && d + 0 < 0.5) exit 0; exit 1 }'; then
    ok "2.5% diverged pair A/C yields a finite positive JC distance ($dAC)"
else
    no "A/C distance not usable (got '$dAC'; nan means too short/too diverse)"
fi

# ---------------------------------------------------------------------------
# 7. symmetry of the matrix: d(A,C) == d(C,A)
# ---------------------------------------------------------------------------
dCA=$(awk 'NR==4 { print $2 }' m1.out)
if [ "$dAC" = "$dCA" ]; then
    ok "matrix symmetric: d(A,C) == d(C,A) == $dAC"
else
    no "matrix asymmetric: d(A,C)=$dAC vs d(C,A)=$dCA"
fi

# ---------------------------------------------------------------------------
# 8. determinism without --bootstrap (prng is only used by bootstrap())
# ---------------------------------------------------------------------------
if "$BIN" --progress=never genomeA.fasta genomeB.fasta genomeC.fasta > m2.out 2>/dev/null \
   && cmp -s m1.out m2.out; then
    ok "repeat run is byte-identical (no PRNG leakage without --bootstrap)"
else
    no "repeat run differs or failed"
fi

# ---------------------------------------------------------------------------
# 9. negative path: a missing input file must not exit 0 (err() -> EXIT_FAILURE)
# ---------------------------------------------------------------------------
if "$BIN" genomeA.fasta does-not-exist.fasta > /dev/null 2>&1; then
    no "missing input file accepted with rc=0"
else
    ok "missing input file rejected with non-zero rc"
fi

# 10. negative path: a single genome is refused (main(): <2 files -> usage)
if "$BIN" genomeA.fasta > /dev/null 2>&1; then
    no "single-genome invocation accepted with rc=0"
else
    ok "single genome rejected with non-zero rc (needs >= 2 files)"
fi

echo "consumer assertions: pass=$pass fail=$fail"
if [ "$fail" -ne 0 ]; then
    # Keep the work dir on failure so the CI log can be tied to real fixtures.
    echo "evidence kept in $W"
    exit 1
fi
cd ..
rm -rf "$W"   # never leave fixtures inside the source tree (not git-ignored)
echo "ALL phylonium CONSUMER TESTS PASSED"
