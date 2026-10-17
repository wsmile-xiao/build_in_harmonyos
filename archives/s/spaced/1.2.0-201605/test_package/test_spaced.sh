#!/bin/sh
# spaced 1.2.0-201605 real-consumer test (run from test_package/conanfile.py).
#
# spaced computes an alignment-free distance matrix over spaced-word
# frequencies, so a genuine consumer test has to hand it real FASTA input and a
# real spaced-seed pattern file and then assert on the matrix it writes.
# Checking that the binary merely starts, or printing a banner, is not a test
# (R34).
#
# The pattern file is what makes the run reproducible: without `-f`, spaced
# spends 5000 iterations of randomised pattern improvement (generator seeded
# from time(0)) and the distances come out different on every run. With `-f` the
# seed set is pinned, so the matrix is bit-identical between runs - which is
# what A15 checks across two different thread counts.
#
# usage: test_spaced.sh <spaced-binary> <workdir>
SPACED="$1"
T="$2"
if [ -z "$SPACED" ] || [ -z "$T" ]; then
    echo "usage: $0 <spaced-binary> <workdir>"
    exit 2
fi

rm -rf "$T"
mkdir -p "$T"

# ── inputs ────────────────────────────────────────────────────────────────────
# Three unrelated DNA sequences, 120/150/90 nt.
cat > "$T/dna.fasta" <<'EOF'
>seq1 test sequence one
CCTGGAGGATGTGCGTGTGAACTGAAGTTTGACCACTTAGTTCATTGATGAATCCGTCTT
CGACAGCTACCGGTGACGTCACGGGATAGCTAGCGTCCACATTTAGTCGACGCTCATAGA
>seq2 test sequence two
GAAGTAACTTGAGTTACACCTTGGCAGCACCATTGGGCGAAGGCCGGGTTAGTCGAGGGG
GTCGTTTGGTCTAAGAATACCCATATCTTTGAATAAATCCCAGGTCGCGAGGTATTGAAA
GACTACTGGTACGGGGGAGGGAGGTATTTC
>seq3 test sequence three
AACTTCTTTTCGCCACATACACGGGCTCATATGAATAACCGCGATTTTTCGAGAGCCCCC
TACGACGGAGGCTGGAACGGTACCGCTAAT
EOF

# Spaced seed of length 5, weight 3 (three match positions, two don't-care).
# Must start and end on a match position or patternset::ReadPattern() rejects it.
printf '11001' > "$T/seed.pattern"

# Three unrelated protein sequences, 30/31/33 aa.
cat > "$T/prot.fasta" <<'EOF'
>prot1 sample protein one
MSTAGKIVCAGWSTRHTLDEKAILQDAVKN
>prot2 sample protein two
MSTAGKIVCAGWSTRHTLDEKIALQDAVKNL
>prot3 sample protein three
MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ
EOF

# ── run ──────────────────────────────────────────────────────────────────────
"$SPACED" -h > "$T/help.out" 2>&1
HELP_RC=$?
"$SPACED" --version > "$T/version.out" 2>&1
VERSION_RC=$?
"$SPACED" -o "$T/dmat.out" -f "$T/seed.pattern" -t 2 "$T/dna.fasta" \
    > "$T/dna.log" 2> "$T/dna.err"
DNA_RC=$?
"$SPACED" -o "$T/prot.out" -f "$T/seed.pattern" -t 2 "$T/prot.fasta" \
    > "$T/prot.log" 2> "$T/prot.err"
PROT_RC=$?
"$SPACED" -o "$T/dmat_t1.out" -f "$T/seed.pattern" -t 1 "$T/dna.fasta" \
    > "$T/dna_t1.log" 2>&1
T1_RC=$?
"$SPACED" -o "$T/dmat_t4.out" -f "$T/seed.pattern" -t 4 "$T/dna.fasta" \
    > "$T/dna_t4.log" 2>&1
T4_RC=$?

echo "[test] spaced -h                                -> RC=$HELP_RC"
echo "[test] spaced --version                          -> RC=$VERSION_RC"
echo "[test] spaced -f seed -t 2 dna.fasta (3 seqs)    -> RC=$DNA_RC"
sed -n '1,5p' "$T/dna.log"
sed -n '1,5p' "$T/dmat.out"
echo "[test] spaced -f seed -t 2 prot.fasta (3 seqs)   -> RC=$PROT_RC"
sed -n '1,5p' "$T/prot.log"
sed -n '1,5p' "$T/prot.out"

FAIL=0
ck() { if eval "$2"; then echo "[A$1] pass: $3"; else echo "[A$1] FAIL: $3"; FAIL=$((FAIL+1)); fi; }

# Row layout of the matrix file (sort.h writeDmat()): line 1 holds the sequence
# count, then one row per sequence, each row being the sequence label followed by
# one field per sequence. The label is the FASTA header truncated to 10 chars, so
# it may itself span several whitespace-separated fields - address the distances
# from the END of the row, whose count comes from the header line.
mval() { awk -v r="$2" -v c="$3" 'NR==1{n=$1; next} NR==r+1{print $(NF-n+c)}' "$1"; }
mlabel() { awk -v r="$2" 'NR==r+1{print $1}' "$1"; }

ck 1  '[ -x "$SPACED" ]' \
    "packaged bin/spaced exists and is executable"
ck 2  '[ $HELP_RC -eq 0 ] && grep -q "Usage:" "$T/help.out"' \
    "spaced -h exits 0 and prints the usage block"
ck 3  'grep -q "spaced word" "$T/help.out" && grep -q -- "-f <file>" "$T/help.out"' \
    "help text advertises the -f pattern-file option used below"
ck 4  '[ $VERSION_RC -eq 0 ]' \
    "spaced --version exits 0 - CI gate L2 probes exactly this and upstream has no --version handler, so this asserts the no-arg path exits cleanly, nothing more"
ck 5  '[ $DNA_RC -eq 0 ] && [ $PROT_RC -eq 0 ] && [ $T1_RC -eq 0 ] && [ $T4_RC -eq 0 ]' \
    "all four spaced invocations exit 0"
ck 6  '[ $DNA_RC -eq 0 ] && ! grep -q "FORMAT-ERROR" "$T/dna.err" && ! grep -q "is an empty file" "$T/dna.err"' \
    "OHOS/aarch64: the -f pattern file is accepted (no plain-char unsigned EOF regression)"
ck 7  'grep -q "3 DNA sequences read" "$T/dna.log"' \
    "FASTA parser counted all 3 DNA sequences"
ck 8  'grep -q "3 protein sequences read" "$T/prot.log"' \
    "FASTA parser takes the protein branch for non-DNA input"
ck 9  '[ -s "$T/dmat.out" ] && [ -s "$T/prot.out" ]' \
    "distance matrix files were written and are non-empty"
ck 10 '[ "$(head -n 1 "$T/dmat.out")" = "3" ]' \
    "matrix header records the sequence count (3)"
ck 11 '[ "$(wc -l < "$T/dmat.out")" = "4" ] && [ "$(wc -l < "$T/prot.out")" = "4" ]' \
    "matrix has exactly one row per sequence (DNA and protein)"
ck 12 '[ "$(mlabel "$T/dmat.out" 1)" = "seq1" ] && [ "$(mlabel "$T/dmat.out" 3)" = "seq3" ] && [ "$(mlabel "$T/prot.out" 1)" = "prot1" ]' \
    "matrix rows carry the FASTA record labels in input order"
# Zero diagonal: self-distance is 0 for every row of both matrices.
ck 13 '[ "$(mval "$T/dmat.out" 1 1)" = "0" ] && [ "$(mval "$T/dmat.out" 2 2)" = "0" ] && [ "$(mval "$T/dmat.out" 3 3)" = "0" ]' \
    "DNA distance matrix has an all-zero diagonal"
ck 14 '[ "$(mval "$T/prot.out" 1 1)" = "0" ] && [ "$(mval "$T/prot.out" 2 2)" = "0" ] && [ "$(mval "$T/prot.out" 3 3)" = "0" ]' \
    "protein distance matrix has an all-zero diagonal"
# Symmetry: d(1,2)==d(2,1), d(1,3)==d(3,1), d(2,3)==d(3,2).
ck 15 '[ -s "$T/dmat.out" ] && [ "$(mval "$T/dmat.out" 1 2)" = "$(mval "$T/dmat.out" 2 1)" ] && [ "$(mval "$T/dmat.out" 1 3)" = "$(mval "$T/dmat.out" 3 1)" ] && [ "$(mval "$T/dmat.out" 2 3)" = "$(mval "$T/dmat.out" 3 2)" ]' \
    "DNA distance matrix is symmetric"
ck 16 '[ -n "$(mval "$T/dmat.out" 1 2)" ] && [ -n "$(mval "$T/dmat.out" 2 3)" ] && [ "$(mval "$T/dmat.out" 1 2)" != "0" ] && [ "$(mval "$T/dmat.out" 2 3)" != "0" ]' \
    "off-diagonal DNA distances are present and non-zero (spaced-word counting really ran)"
ck 17 '[ -n "$(mval "$T/prot.out" 1 2)" ] && [ "$(mval "$T/prot.out" 1 2)" != "0" ]' \
    "off-diagonal protein distance is present and non-zero (protein branch really counts)"
# The -f seed set pins the computation, so the result may not depend on -t.
ck 18 'cmp -s "$T/dmat_t1.out" "$T/dmat_t4.out" && cmp -s "$T/dmat_t1.out" "$T/dmat.out"' \
    "identical matrix for -t 1, -t 2 and -t 4 (OpenMP reduction is deterministic)"

echo "ASSERTS=18 PASS=$((18-FAIL)) FAIL=$FAIL"
[ "$FAIL" = 0 ] || exit 1
exit 0
