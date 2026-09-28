#!/bin/sh
# Functional test suite for the packaged seq-gen executable.
#
# Usage: sh test_seq_gen.sh <bin-dir>
#
# Upstream Seq-Gen ships no test framework at all (test/ holds only the data
# file ZIKV_100.newick.trees and the Makefile has no check/test target), so
# these cases are the补全 suite: they cover every documented CLI mode with
# exact assertions on the emitted alignment.
#
# Counting convention (used identically in MANIFEST.yml, notes.md and the PR
# tables): one independent check item per assertion, each printing
# ok/FAIL and individually decidable.  20 items, F1-F20.
#
# Exit code 0 = all items passed, 1 = at least one failure.
set -u
if (set -o pipefail) 2>/dev/null; then
    set -o pipefail
fi

bin_dir=${1:?usage: test_seq_gen.sh <bin-dir>}
SG="$bin_dir/seq-gen"

if [ ! -f "$SG" ]; then
    printf 'FAIL: seq-gen not found in %s\n' "$bin_dir" >&2
    exit 1
fi
if [ ! -x "$SG" ]; then
    printf 'FAIL: seq-gen is not executable: %s\n' "$SG" >&2
    exit 1
fi

# OHOS / is largely read-only (erofs) and /tmp may not be writable, so every
# scratch file goes under a TMPDIR we create ourselves.
work="${TMPDIR:-/tmp}/seq-gen-test.$$"
if ! mkdir -p "$work" 2>/dev/null; then
    work="./seq-gen-test.$$"
    mkdir -p "$work" || { printf 'FAIL: no writable scratch dir\n' >&2; exit 1; }
fi
trap 'rm -rf "$work"' EXIT HUP INT TERM

# Upstream's own examples/example.tree content (4 taxa).
tree4="$work/t4.tree"
printf '%s\n' '(((Taxon1:0.2,Taxon2:0.2):0.1,Taxon3:0.3):0.1,Taxon4:0.4);' > "$tree4"
# Two 3-taxon trees in one file.
tree2x3="$work/t2x3.tree"
printf '%s\n%s\n' '((A:0.1,B:0.1):0.1,C:0.2);' '((A:0.1,B:0.1):0.1,C:0.2);' > "$tree2x3"

pass=0
fail=0

ok() {
    pass=$((pass + 1))
    printf 'ok %s: %s\n' "$1" "$2"
}

bad() {
    fail=$((fail + 1))
    printf 'FAIL %s: %s\n' "$1" "$2" >&2
}

# ---------------------------------------------------------------- F1
out="$work/f1.out"; err="$work/f1.err"
"$SG" -h >"$out" 2>"$err"
rc=$?
if [ "$rc" -eq 0 ]; then
    ok F1_help_exit_zero "-h exits 0 (rc=$rc)"
else
    bad F1_help_exit_zero "-h exited rc=$rc"
fi

# ---------------------------------------------------------------- F2
if grep -q '^Usage: seq-gen' "$err"; then
    ok F2_help_usage_text "stderr carries the 'Usage: seq-gen' synopsis"
else
    bad F2_help_usage_text "no usage synopsis in stderr: $(head -c 120 "$err")"
fi

# ---------------------------------------------------------------- F3
if grep -q 'Version 1\.3\.5' "$err"; then
    ok F3_version_banner "banner reports 'Version 1.3.5' (packaged upstream version)"
else
    bad F3_version_banner "version banner missing: $(head -c 120 "$err")"
fi

# ---------------------------------------------------------------- F4
"$SG" >/dev/null 2>"$work/f4.err"
rc=$?
# The usage text must be present too: a binary that fails to exec at all also
# exits non-zero, and that must not be mistaken for a clean rejection.
if [ "$rc" -ne 0 ] && grep -q '^Usage: seq-gen' "$work/f4.err"; then
    ok F4_no_args_rejected "no arguments is rejected with the usage text (rc=$rc)"
else
    bad F4_no_args_rejected "rc=$rc, usage lines=$(grep -c '^Usage: seq-gen' "$work/f4.err")"
fi

# ---------------------------------------------------------------- F5
"$SG" -m BOGUS -l 10 "$tree4" >/dev/null 2>"$work/f5.err"
rc=$?
# seq-gen reports "Unknown Model: <name>" for an unrecognised -m value; that
# message (not just a non-zero exit) proves the binary really ran.
if [ "$rc" -ne 0 ] && grep -q '^Unknown Model: BOGUS' "$work/f5.err"; then
    ok F5_bad_model_rejected "unknown model rejected with 'Unknown Model: BOGUS' (rc=$rc)"
else
    bad F5_bad_model_rejected "rc=$rc, stderr=$(head -c 80 "$work/f5.err")"
fi

# ---------------------------------------------------------------- F6
fasta="$work/f6.fasta"
"$SG" -m HKY -l 60 -z 12345 "$tree4" >"$fasta" 2>"$work/f6.err"
rc=$?
n=$(grep -c '^>' "$fasta")
if [ "$rc" -eq 0 ] && [ "$n" -eq 4 ]; then
    ok F6_hky_taxa_count "HKY simulation on a 4-taxon tree emits exactly 4 records (got $n)"
else
    bad F6_hky_taxa_count "rc=$rc records=$n (expected 4)"
fi

# ---------------------------------------------------------------- F7
len_bad=$(awk '/^>/ { next } { if (length($0) != 60) print NR": "length($0) }' "$fasta")
if [ -z "$len_bad" ]; then
    ok F7_sequence_length "every sequence honours -l 60"
else
    bad F7_sequence_length "wrong sequence length at lines: $len_bad"
fi

# ---------------------------------------------------------------- F8
alpha_bad=$(awk '/^>/ { next } { if ($0 ~ /[^ACGT]/) print NR": "$0 }' "$fasta")
if [ -z "$alpha_bad" ]; then
    ok F8_dna_alphabet "nucleotide output uses the ACGT alphabet only"
else
    bad F8_dna_alphabet "non-ACGT characters: $alpha_bad"
fi

# ---------------------------------------------------------------- F9
again="$work/f9.fasta"
"$SG" -m HKY -l 60 -z 12345 "$tree4" >"$again" 2>/dev/null
if cmp -s "$fasta" "$again"; then
    ok F9_seed_reproducible "the same -z seed reproduces a byte-identical alignment"
else
    bad F9_seed_reproducible "same seed produced different output"
fi

# ---------------------------------------------------------------- F10
other="$work/f10.fasta"
"$SG" -m HKY -l 60 -z 4242 "$tree4" >"$other" 2>/dev/null
if cmp -s "$fasta" "$other"; then
    bad F10_seed_sensitive "a different -z seed produced identical output (RNG not seeded)"
else
    ok F10_seed_sensitive "a different -z seed produces a different alignment"
fi

# ---------------------------------------------------------------- F11
phy="$work/f11.phy"
"$SG" -m HKY -l 60 -z 12345 -op "$tree4" >"$phy" 2>/dev/null
head1=$(head -1 "$phy")
case "$head1" in
    *"4 60"*) ok F11_phylip_header "PHYLIP (-op) header declares '4 60' (ntaxa nchar), got '$head1'" ;;
    *) bad F11_phylip_header "unexpected PHYLIP header: '$head1'" ;;
esac

# ---------------------------------------------------------------- F12
if awk 'NR>1 && NF==2 && $1=="Taxon1" { found=1 } END { exit !found }' "$phy"; then
    ok F12_phylip_rows "PHYLIP body has one fixed-width row per taxon"
else
    bad F12_phylip_rows "PHYLIP body malformed: $(head -3 "$phy" | tr '\n' '|')"
fi

# ---------------------------------------------------------------- F13
rphy="$work/f13.phy"
"$SG" -m HKY -l 60 -z 12345 -or "$tree4" >"$rphy" 2>/dev/null
if awk 'NR==2 && $1=="Taxon1" && length($2)==60 { found=1 } END { exit !found }' "$rphy"; then
    ok F13_relaxed_phylip "relaxed PHYLIP (-or) uses single-space name separation"
else
    bad F13_relaxed_phylip "unexpected relaxed PHYLIP output: $(sed -n 2p "$rphy")"
fi

# ---------------------------------------------------------------- F14
nex="$work/f14.nex"
"$SG" -m HKY -l 60 -z 12345 -on "$tree4" >"$nex" 2>/dev/null
if [ "$(head -1 "$nex")" = "#NEXUS" ]; then
    ok F14_nexus_header "NEXUS (-on) output starts with #NEXUS"
else
    bad F14_nexus_header "first line is '$(head -1 "$nex")'"
fi

# ---------------------------------------------------------------- F15
aa="$work/f15.fasta"
"$SG" -m WAG -l 30 -z 12345 "$tree4" >"$aa" 2>/dev/null
aa_bad=$(awk '/^>/ { next } { if ($0 ~ /[^ARNDCQEGHILKMFPSTWYV]/) print NR": "$0 }' "$aa")
aa_n=$(grep -c '^>' "$aa")
if [ "$aa_n" -eq 4 ] && [ -z "$aa_bad" ]; then
    ok F15_amino_acid_model "WAG amino-acid model emits 4 records over the 20-letter alphabet"
else
    bad F15_amino_acid_model "records=$aa_n invalid_chars=$aa_bad"
fi

# ---------------------------------------------------------------- F16
two="$work/f16.fasta"
"$SG" -m HKY -l 60 -z 12345 -n 2 "$tree4" >"$two" 2>/dev/null
n=$(grep -c '^>' "$two")
if [ "$n" -eq 8 ]; then
    ok F16_multiple_datasets "-n 2 emits 2 datasets x 4 taxa = 8 records (got $n)"
else
    bad F16_multiple_datasets "expected 8 records, got $n"
fi

# ---------------------------------------------------------------- F17
gamma="$work/f17.fasta"
"$SG" -m HKY -l 60 -z 12345 -a 0.5 -g 4 "$tree4" >"$gamma" 2>/dev/null
rc=$?
n=$(grep -c '^>' "$gamma")
glen=$(awk '/^>/ { next } { if (length($0) != 60) print NR }' "$gamma")
if [ "$rc" -eq 0 ] && [ "$n" -eq 4 ] && [ -z "$glen" ]; then
    ok F17_gamma_rates "gamma rate heterogeneity (-a 0.5 -g 4) still yields 4 x 60"
else
    bad F17_gamma_rates "rc=$rc records=$n bad_length_lines=$glen"
fi

# ---------------------------------------------------------------- F18
multi="$work/f18.fasta"
"$SG" -m HKY -l 30 -z 12345 "$tree2x3" >"$multi" 2>/dev/null
n=$(grep -c '^>' "$multi")
if [ "$n" -eq 6 ]; then
    ok F18_multi_tree_file "a 2-tree file yields 2 x 3 taxa = 6 records (got $n)"
else
    bad F18_multi_tree_file "expected 6 records, got $n"
fi

# ---------------------------------------------------------------- F19
sep="$work/f19"
mkdir -p "$sep"
( cd "$sep" && "$SG" -m HKY -l 30 -z 12345 -of "$tree4" >/dev/null 2>&1 )
if [ -s "$sep/output_1.fasta" ] && [ "$(grep -c '^>' "$sep/output_1.fasta")" -eq 4 ]; then
    ok F19_separate_files "-of writes output_1.fasta with 4 records into a writable cwd"
else
    bad F19_separate_files "output_1.fasta missing or wrong: $(ls "$sep" | tr '\n' ' ')"
fi

# ---------------------------------------------------------------- F20
anc="$work/f20.fasta"
"$SG" -m HKY -l 30 -z 12345 -wa "$tree4" >"$anc" 2>/dev/null
n=$(grep -c '^>' "$anc")
if [ "$n" -gt 4 ]; then
    ok F20_ancestral_output "-wa additionally emits internal-node ancestral sequences ($n records > 4 tips)"
else
    bad F20_ancestral_output "expected extra ancestral records, got $n"
fi

printf '\nSEQ_GEN_FUNCTIONAL={"discovered": %d, "passed": %d, "failed": %d}\n' \
    "$((pass + fail))" "$pass" "$fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
