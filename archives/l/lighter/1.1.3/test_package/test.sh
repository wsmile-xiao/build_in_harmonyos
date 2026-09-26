#!/bin/sh
# test_package/test.sh - functional tests for the packaged lighter executable.
#
# Upstream Lighter 1.1.3 ships no test suite (see notes.md), so every assertion
# below is consumer-side and executes the real packaged binary. Every external
# call is wrapped in /usr/bin/timeout; rc=124 therefore fails the run.
#
# Two behaviours of Lighter 1.1.3 were measured on the target and shaped these
# tests (both are disclosed in notes.md):
#   * FASTQ output separates records with a trailing blank line, so a corrected
#     12-read FASTQ is 60 lines, not 48: records are parsed header-anchored, never
#     with an NR % 4 position assumption.
#   * `-k` takes kmer_length, genome_size and alpha; the trusted-kmer cut-off is
#     derived from them (genome_size is in bases). On a 12-read toy the defaults
#     make every k-mer trusted and Lighter reports "Corrected 0 bases", so the
#     run below pins `genome_size` to the scale of the fixture (1000 bases).
#     A single substitution is therefore NOT collapsed by the spectrum statistics
#     and is asserted as preserved verbatim; what Lighter does correct on this
#     scale is a read carrying an invalid base (see assertion 5).
set -eu

T=/usr/bin/timeout
if [ ! -x "$T" ]; then
    echo "FAIL: /usr/bin/timeout not present"
    exit 1
fi

n=0
ok() {
    n=$((n + 1))
    printf 'PASS %d: %s\n' "$n" "$1"
}

BIN="$(command -v lighter || true)"
if [ -z "$BIN" ]; then
    echo "FAIL: lighter not found in conanrun PATH"
    exit 1
fi
echo "[test] binary under test: $BIN"

# Run in a throwaway scratch directory: device /tmp is read-only, so use
# $HOME/tmp. Fixtures and lighter output must never land in the archive dir.
# CI worker 的 $HOME 下没有 tmp/ ⇒ 旧写法 `mktemp -d "$HOME/tmp/..."` 直接
# `Failed to create directory ...: No such file or directory`（test() line 18 整体失败）。
# ⇒ 先建父目录；建不出来就退到当前可写目录下的 .lighter-tmp（绝不退到只读 /tmp）。
# 本地已按复刻 worker 的 A/B 验证：旧式在同一隔离环境下复现同一句 ENOENT，新式成功建出
# 且不撞名可重复执行。TMPROOT 优先 $TMPDIR，保持对已有环境的尊重。
TMPROOT="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPROOT" 2>/dev/null || { TMPROOT="$PWD/.lighter-tmp"; mkdir -p "$TMPROOT"; }
WORK="$(mktemp -d "$TMPROOT/lighter-test.XXXXXX")"
cd "$WORK"
trap 'cd /; rm -rf "$WORK"' EXIT HUP INT TERM
echo "[test] scratch dir: $WORK"

TPL=ATGCTAACAGTCGCGATCGATCGGATCCCTTAAGGCCTTACGATGCAAGGTCAGACGTGACTGAGCTTACCGGAT
MUT=ATGCTAACAGTCGCGATCGATCGGATCCCTTAAGGCCTAACGATGCAAGGTCAGACGTGACTGAGCTTACCGGAT
NRD=ATGCTAACAGTCGCGATCGATCGGATCCCTTAAGGCCTNACGATGCAAGGTCAGACGTGACTGAGCTTACCGGAT
QUAL=IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII

# seqs FILE - the sequence line of every FASTQ record, parsed header-anchored so
# the blank record separators cannot shift the record layout.
seqs() {
    grep -A1 [@]read "$1" | grep -v ^@ | grep -v ^-
}
# records FILE - 11 identical template reads plus one outlier passed in $2.
mkfq() {
    i=1
    : > "$1"
    while [ "$i" -le 11 ]; do
        printf '@read%02d\n%s\n+\n%s\n' "$i" "$TPL" "$QUAL" >> "$1"
        i=$((i + 1))
    done
    printf '@read12\n%s\n+\n%s\n' "$2" "$QUAL" >> "$1"
}

# ---------------------------------------------------------- assertion 1
usage="$($T 60 lighter 2>&1 || true)"
printf '%s\n' "$usage" > usage.txt
grep -q "Usage:" usage.txt
ok "bare invocation prints the usage banner (captured to usage.txt)"

# ---------------------------------------------------------- assertions 2-4
# 11 copies of one 76 nt template plus one read carrying a single substitution,
# run with genome_size matched to the fixture (see header comment).
mkfq in.fq "$MUT"
$T 300 lighter -k 21 1000 1 -r in.fq -od . > run.log 2>&1
test -s in.cor.fq
ok "FASTQ run exits 0 and produces non-empty in.cor.fq"

test "$($T 60 grep -c '^@read' in.cor.fq)" = 12
test "$($T 60 grep -c '^+$' in.cor.fq)" = 12
ok "FASTQ output carries 12 records (12 headers, 12 quality separators) in Lighter's blank-line-separated framing"

test "$($T 60 grep -c 'Corrected 0 bases' run.log)" = 1
test "$(seqs in.cor.fq | $T 60 sort -u | $T 60 wc -l)" = 2
test "$(seqs in.cor.fq | $T 60 grep -c "$TPL")" = 11
test "$(seqs in.cor.fq | $T 60 grep -c "$MUT")" = 1
ok "the k-mer spectrum leaves the 12 substituted read verbatim (11x template + 1x outlier, Corrected 0 bases)"

# ---------------------------------------------------------- assertion 5
# An invalid base is the case that does exercise the encoding table: nucToNum[]
# marks non-ACGT with a -1 sentinel, so the kmers touching it are untrusted and
# Lighter must correct that read back onto the 11x template.
mkfq inN.fq "$NRD"
$T 300 lighter -k 21 1000 1 -r inN.fq -od . > runN.log 2>&1
test -s inN.cor.fq
test "$($T 60 grep -c 'Corrected 1 bases' runN.log)" = 1
test "$($T 60 grep -c '^@read12 cor$' inN.cor.fq)" = 1
test "$(seqs inN.cor.fq | $T 60 sort -u | $T 60 wc -l)" = 1
test "$(seqs inN.cor.fq | $T 60 sort -u)" = "$TPL"
ok "a read carrying an invalid base is corrected onto the template (Corrected 1 bases, header tagged cor, 12 identical output reads)"

# ---------------------------------------------------------- assertions 6-7
# Gzipped FASTQ exercises the zlib link face end to end (gzread in, gzwrite out);
# the result is re-inflated with an independent decompressor.
$T 60 gzip -c in.fq > gztest.fq.gz
$T 300 lighter -k 21 1000 1 -r gztest.fq.gz -od . > run-gz.log 2>&1
test -s gztest.cor.fq.gz
magic="$($T 30 od -An -tx1 -N2 gztest.cor.fq.gz | $T 30 tr -d ' \n')"
test "$magic" = "1f8b"
ok "gzipped FASTQ input yields a non-empty gzip-framed gztest.cor.fq.gz"

$T 60 gzip -dc gztest.cor.fq.gz > gztest.cor.fq
test -s gztest.cor.fq
test "$($T 60 grep -c '^@read' gztest.cor.fq)" = 12
test "$(seqs gztest.cor.fq | $T 60 sort -u | $T 60 wc -l)" = 2
ok "the gzip output inflates back to the same 12-record, 2-sequence corrected set"

# ---------------------------------------------------------- assertion 8
# FASTA input takes the same zlib-capable reader but a different record writer.
i=1
: > in.fa
while [ "$i" -le 11 ]; do
    printf '>read%02d\n%s\n' "$i" "$TPL" >> in.fa
    i=$((i + 1))
done
printf '>read12\n%s\n' "$MUT" >> in.fa
$T 300 lighter -k 21 1000 1 -r in.fa -od . > run-fa.log 2>&1
test -s in.cor.fa
test "$($T 60 grep -c '^>read' in.cor.fa)" = 12
ok "FASTA input yields in.cor.fa carrying all 12 records"

# ---------------------------------------------------------- assertion 9
# Link face. zlib/1.3.2 is packaged static-only in this repository (R26), so
# DT_NEEDED carries no libz.so; the dependency is instead proven resolved inside
# the artifact: gzread is defined and is not an undefined reference.
ELF=""
for d in /data/service/hnp/bin /usr/bin /bin "$HOME/usr/local/bin"; do
    if [ -x "$d/readelf" ]; then
        ELF="$d/readelf"
        break
    fi
done
if [ -z "$ELF" ]; then
    echo "FAIL: no readelf found to inspect the ELF symbol table"
    exit 1
fi
$T 60 "$ELF" -d "$BIN" > dyn.txt 2>/dev/null || true
$T 60 "$ELF" -sW "$BIN" > syms.txt 2>/dev/null || true
grep -q "gzread" syms.txt
if grep -q "UND gzread" syms.txt; then
    echo "FAIL: gzread is an undefined reference, zlib was not linked in"
    exit 1
fi
ok "zlib is linked into the artifact (gzread defined locally, no UND gzread)"

echo "[test] assertions passed: $n"
