#!/usr/bin/env bash
# test_miniprot.sh — functional test for the miniprot protein-to-genome aligner.
# Runs in conanrun env (PATH includes the installed package bin/).
#
# Fixture (deterministic, programmatically generated, text-only):
#   testdata/genome.fa    ctg1: forward-strand 2-exon synthetic gene encoding
#                         avGFP 239aa (150bp GT..AG intron, fixed-seed flanks)
#                         ctg2: reverse-strand intronless copy of the same CDS
#   testdata/protein.fa   avGFP 239aa query
#   testdata/random_neg.fa 80aa random protein unrelated to the genome
#
# 12 assertions: version, PAF hit count, + strand hit fields, N intron cigar,
# - strand hit fields, coverage columns, AS score, cs tag, GFF header,
# GFF mRNA/CDS structure, negative random protein, negative missing file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTDATA="$SCRIPT_DIR/testdata"
WORK="$(pwd)/miniprot-testdata"
rm -rf "$WORK" && mkdir -p "$WORK"

# --------------------------------------------------------------------------
# Test 1: version — `miniprot --version` prints "0.18-r281" and exits 0.
# --------------------------------------------------------------------------
if version_out="$(miniprot --version 2>&1)" && echo "$version_out" | grep -q "0.18-r281"; then
    echo "PASS [1/12]: miniprot version is 0.18-r281"
else
    echo "FAIL [1/12]: unexpected version output: $version_out"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 2: real alignment — protein vs genome, default PAF output.
# Expect exactly 2 hits: ctg1 (forward, spliced) and ctg2 (reverse).
# --------------------------------------------------------------------------
miniprot "$TESTDATA/genome.fa" "$TESTDATA/protein.fa" > "$WORK/aln.paf" 2>"$WORK/aln.log"
paf_lines=$(grep -vc '^$' "$WORK/aln.paf" || true)
if [ "$paf_lines" -eq 2 ]; then
    echo "PASS [2/12]: PAF output has exactly 2 hits"
else
    echo "FAIL [2/12]: expected 2 PAF hits, got $paf_lines"
    cat "$WORK/aln.paf"
    exit 1
fi

# ctg1 hit: forward strand, full query coverage, spliced alignment
ctg1=$(awk -F'\t' '$6=="ctg1"' "$WORK/aln.paf")
if [ -n "$ctg1" ]; then
    echo "PASS [3/12]: ctg1 hit present (forward strand target)"
else
    echo "FAIL [3/12]: no hit for ctg1"
    exit 1
fi

# Test 4: ctg1 fields — strand '+', query fully covered (0..239),
# alignment block 717/717 (239*3 nt, no gaps)
echo "$ctg1" | awk -F'\t' '
    $5=="+" && $3==0 && $4==239 && $10==717 && $11==717 {
        print "PASS [4/12]: ctg1 strand/query-range/coverage correct (+, 0-239, 717/717)"
        exit 0
    }
    { printf "FAIL [4/12]: ctg1 fields wrong: strand=%s q=%s-%s blk=%s/%s\n", $5, $3, $4, $10, $11; exit 1 }
'

# Test 5: ctg1 models the intron — cigar contains N (intron) operation
cg1=$(echo "$ctg1" | grep -o 'cg:Z:[^	]*' | sed 's/cg:Z://')
if echo "$cg1" | grep -qE '[0-9]+N'; then
    echo "PASS [5/12]: ctg1 cigar contains intron (N) operations"
else
    echo "FAIL [5/12]: ctg1 cigar has no N operation: $cg1"
    exit 1
fi

# Test 6: ctg2 hit — reverse strand, full coverage
ctg2=$(awk -F'\t' '$6=="ctg2"' "$WORK/aln.paf")
echo "$ctg2" | awk -F'\t' '
    $5=="-" && $3==0 && $4==239 && $10==717 && $11==717 {
        print "PASS [6/12]: ctg2 hit on reverse strand with full coverage (-, 0-239, 717/717)"
        exit 0
    }
    { printf "FAIL [6/12]: ctg2 fields wrong: strand=%s q=%s-%s blk=%s/%s\n", $5, $3, $4, $10, $11; exit 1 }
'

# Test 7: alignment score tag present and positive (AS:i:)
as1=$(echo "$ctg1" | grep -o 'AS:i:[0-9]*' | head -1 | sed 's/AS:i://')
if [ -n "$as1" ] && [ "$as1" -gt 0 ]; then
    echo "PASS [7/12]: ctg1 has positive AS score (AS:i:$as1)"
else
    echo "FAIL [7/12]: missing/invalid AS tag on ctg1 hit"
    exit 1
fi

# Test 8: cs:Z consistency-sequence tag present (miniprot-specific tag)
if echo "$ctg1" | grep -q 'cs:Z:'; then
    echo "PASS [8/12]: cs:Z alignment tag present"
else
    echo "FAIL [8/12]: cs:Z tag missing on ctg1 hit"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 9-10: GFF output — header + mRNA/CDS structure.
# --------------------------------------------------------------------------
miniprot --gff "$TESTDATA/genome.fa" "$TESTDATA/protein.fa" > "$WORK/aln.gff" 2>/dev/null
if head -1 "$WORK/aln.gff" | grep -q '^##gff-version 3'; then
    echo "PASS [9/12]: GFF output starts with ##gff-version 3"
else
    echo "FAIL [9/12]: GFF version header missing"
    head -3 "$WORK/aln.gff"
    exit 1
fi

mrna_n=$(awk -F'\t' '$3=="mRNA"' "$WORK/aln.gff" | wc -l)
cds_n=$(awk -F'\t' '$3=="CDS"' "$WORK/aln.gff" | wc -l)
cds_ctg1=$(awk -F'\t' '$1=="ctg1" && $3=="CDS"' "$WORK/aln.gff" | wc -l)
if [ "$mrna_n" -eq 2 ] && [ "$cds_n" -ge 3 ] && [ "$cds_ctg1" -eq 2 ]; then
    echo "PASS [10/12]: GFF has 2 mRNA and $cds_n CDS features (ctg1 spliced into 2 exons)"
else
    echo "FAIL [10/12]: GFF structure wrong (mRNA=$mrna_n CDS=$cds_n ctg1-CDS=$cds_ctg1)"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 11: negative input — random unrelated protein must yield ZERO hits.
# Explicit check of real behavior (no || true masking); empty output + rc 0
# is the documented upstream behavior for "no alignment found".
# --------------------------------------------------------------------------
neg_rc=0
miniprot "$TESTDATA/genome.fa" "$TESTDATA/random_neg.fa" > "$WORK/neg.paf" 2>/dev/null || neg_rc=$?
neg_lines=$(grep -vc '^$' "$WORK/neg.paf" || true)
if [ "$neg_rc" -eq 0 ] && [ "$neg_lines" -eq 0 ]; then
    echo "PASS [11/12]: unrelated random protein produces no alignments (rc=0, 0 hits)"
else
    echo "FAIL [11/12]: negative input unexpectedly aligned (rc=$neg_rc, $neg_lines hits)"
    cat "$WORK/neg.paf"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 12: negative input — missing reference file must fail with rc=1 and
# a real error message on stderr (upstream prints "[ERROR] failed to
# open/build the index").
# --------------------------------------------------------------------------
miss_rc=0
miniprot "$TESTDATA/does-not-exist.fa" "$TESTDATA/protein.fa" > "$WORK/miss.paf" 2>"$WORK/miss.log" || miss_rc=$?
if [ "$miss_rc" -ne 0 ] && grep -qi "failed to open" "$WORK/miss.log"; then
    echo "PASS [12/12]: missing input file rejected with rc=$miss_rc and error message"
else
    echo "FAIL [12/12]: missing-file error behavior wrong (rc=$miss_rc)"
    cat "$WORK/miss.log"
    exit 1
fi

rm -rf "$WORK"
echo "ALL TESTS PASSED (12/12)"
exit 0
