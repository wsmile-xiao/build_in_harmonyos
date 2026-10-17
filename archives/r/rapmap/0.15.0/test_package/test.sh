#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for rapmap 0.15.0
#
# Runs in the conanrun env, so `rapmap` resolves to the packaged bin/rapmap.
# Real end-to-end scenario: synthesise a deterministic transcriptome plus a
# paired-end read set taken verbatim from it, build the quasi-mapping index
# twice (plain and --perfectHash), map, then assert the SAM is well formed and
# contains genuinely mapped alignments against our own transcript names.
#
# The quasiindex / quasimap invocation forms are the ones upstream itself
# exercises in cmake/TestQuasiMap.cmake, so no CLI syntax is invented here.
# Assertions use portable awk bit arithmetic (int($2/4)%2) rather than gawk's
# and(), so the test does not depend on a GNU awk extension.
set -eu

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
# bash trusts PWD over a failed getcwd() syscall; seed it for HMDFS dirs.
PWD="$(pwd)"
export PWD

pass=0
fail=0
ok()  { echo "PASS: $1"; pass=$((pass+1)); }
bad() { echo "FAIL: $1"; fail=$((fail+1)); }

# run <label> <cmd...> : run a command, record its status and combined output.
# Never propagates a non-zero status: with `set -eu` a single failing step would
# abort the script and hide every later assertion, so failures are accumulated
# into $fail and the final summary decides the exit code.
run() {
  local label="$1"; shift
  if "$@" > "${label}.log" 2>&1; then
    ok "$label exited 0"
  else
    bad "$label exited non-zero (see ${label}.log)"
    sed -n '1,20p' "${label}.log" | sed 's/^/       | /'
  fi
  return 0
}

echo "[test] rapmap resolves from the conan run environment"
if command -v rapmap >/dev/null 2>&1; then
  ok "rapmap found on PATH ($(command -v rapmap))"
else
  echo "FAIL: rapmap not found in conanrun PATH"; exit 1
fi

# --- 1. version / usage surface --------------------------------------------
echo "[test] rapmap --version"
run ver bash -c 'rapmap --version'
ver_out="$(cat ver.log)"
case "$ver_out" in
  rapmap\ *) ok "--version prints the rapmap banner ($ver_out)" ;;
  *)         bad "--version output unexpected: $ver_out" ;;
esac
# NOTE: upstream hard-codes its internal version string to "0.6.0" in
# include/RapMapConfig.hpp, so the banner reads "rapmap 0.6.0" while the Conan
# package version is 0.15.0 (= upstream tag salmon-v0.15.0).  We assert the
# banner shape, not the number, and deliberately do not patch that string.

echo "[test] rapmap --help"
run help bash -c 'rapmap --help'
if grep -q quasiindex help.log; then ok "--help documents the quasiindex subcommand"; else bad "--help lacks quasiindex"; fi
if grep -q quasimap   help.log; then ok "--help documents the quasimap subcommand";   else bad "--help lacks quasimap";   fi

# --- 2. deterministic corpus ------------------------------------------------
gen_seq() { # gen_seq <len> <seed> -> deterministic pseudo-random ACGT
  local len=$1 seed=$2 i v s=""
  for ((i = 0; i < len; i++)); do
    v=$(( ((seed * 1103515245 + i * 12345 + i * i * 2654435761) >> 13) & 3 ))
    case $v in
      0) s+="A" ;; 1) s+="C" ;; 2) s+="G" ;; 3) s+="T" ;;
    esac
  done
  printf "%s" "$s"
}

TLEN=600
RL=100
txA="$(gen_seq $TLEN 7)"
txB="$(gen_seq $TLEN 1234567)"

{
  printf '>TRNA length=%s effective_length=%s\n%s\n' "$TLEN" "$((TLEN - RL + 1))" "$txA"
  printf '>TRNB length=%s effective_length=%s\n%s\n' "$TLEN" "$((TLEN - RL + 1))" "$txB"
} > transcripts.fa

QUAL="$(printf 'I%.0s' $(seq 1 $RL))"
: > reads_1.fastq
: > reads_2.fastq
tx=("$txA" "$txA" "$txB" "$txB")
o1=(5   200 40   300)
o2=(120 320 160  400)
for ((k = 0; k < 4; k++)); do
  printf '@read%d/1\n%s\n+\n%s\n' $((k+1)) "${tx[k]:${o1[k]}:$RL}" "$QUAL" >> reads_1.fastq
  printf '@read%d/2\n%s\n+\n%s\n' $((k+1)) "${tx[k]:${o2[k]}:$RL}" "$QUAL" >> reads_2.fastq
done

if [ "$(grep -c '^>' transcripts.fa)" -eq 2 ]; then ok "corpus: transcripts.fa holds 2 records"; else bad "corpus: wrong transcript count"; fi
if [ "$(wc -l < reads_1.fastq)" -eq 16 ] && [ "$(wc -l < reads_2.fastq)" -eq 16 ]; then
  ok "corpus: 4 read pairs written to both fastq files"
else
  bad "corpus: unexpected fastq line counts ($(wc -l < reads_1.fastq)/$(wc -l < reads_2.fastq))"
fi
qlen="$(awk 'NR%4==2{print length($0); exit}' reads_1.fastq)"
qqlen="$(awk 'NR%4==0{print length($0); exit}' reads_1.fastq)"
if [ "$qlen" -eq "$RL" ] && [ "$qqlen" -eq "$RL" ]; then
  ok "corpus: read and quality strings both ${RL} bases long"
else
  bad "corpus: read/quality length mismatch ($qlen/$qqlen)"
fi

# --- 3. quasiindex ----------------------------------------------------------
echo "[test] rapmap quasiindex -t transcripts.fa -i idx_plain"
run idx_plain bash -c 'rapmap quasiindex -t transcripts.fa -i idx_plain'
if [ -d idx_plain ]; then ok "quasiindex created the index directory"; else bad "quasiindex created no directory"; fi
# src/RapMapSAIndexer.cpp writes <dir>/quasi_index.log and <dir>/refInfo.json
if [ -s idx_plain/quasi_index.log ]; then ok "quasiindex wrote a non-empty quasi_index.log"; else bad "quasi_index.log missing/empty"; fi
if [ -s idx_plain/refInfo.json ];    then ok "quasiindex wrote a non-empty refInfo.json";    else bad "refInfo.json missing/empty"; fi
nidx="$(find idx_plain -type f | wc -l)"
if [ "$nidx" -ge 3 ]; then ok "quasiindex produced $nidx index payload files"; else bad "only $nidx index files produced"; fi

echo "[test] rapmap quasiindex --perfectHash -t transcripts.fa -i idx_ph"
run idx_ph bash -c 'rapmap quasiindex --perfectHash -t transcripts.fa -i idx_ph'
if [ -d idx_ph ] && [ -s idx_ph/refInfo.json ]; then
  ok "--perfectHash index built and self-describes via refInfo.json"
else
  bad "--perfectHash index incomplete"
fi

# --- 4. quasimap ------------------------------------------------------------
MAP_AWK='!/^@/ && int($2/4)%2==0 && $3!="*" {n++} END{print n+0}'

echo "[test] rapmap quasimap against the plain index"
run map_plain bash -c 'rapmap quasimap -t 2 -i idx_plain -1 reads_1.fastq -2 reads_2.fastq -o out_plain.sam'
if [ -s out_plain.sam ]; then ok "quasimap produced a non-empty out_plain.sam"; else bad "out_plain.sam missing/empty"; fi
if head -1 out_plain.sam | grep -q '^@HD'; then ok "SAM starts with an @HD header line"; else bad "SAM has no @HD header"; fi
nsq="$(grep -c '^@SQ' out_plain.sam)"
if [ "$nsq" -eq 2 ]; then ok "SAM declares both transcripts in @SQ"; else bad "@SQ count is $nsq, expected 2"; fi

mapped="$(awk "$MAP_AWK" out_plain.sam)"
echo "       mapped alignment records (plain index): ${mapped}"
if [ "$mapped" -ge 1 ]; then ok "quasimap reports mapped alignments (>=1)"; else bad "quasimap reported no mapped alignment"; fi

badref="$(awk -v OFS='\t' '!/^@/ && int($2/4)%2==0 && $3!="*" {print $3}' out_plain.sam \
         | sort -u | grep -v -e '^TRNA$' -e '^TRNB$' | wc -l)"
if [ "$badref" -eq 0 ]; then ok "every mapped RNAME refers to one of our transcripts"; else bad "$badref unexpected RNAME(s) in output"; fi

echo "[test] rapmap quasimap against the --perfectHash index"
run map_ph bash -c 'rapmap quasimap -t 2 -i idx_ph -1 reads_1.fastq -2 reads_2.fastq -o out_ph.sam'
if [ -s out_ph.sam ]; then ok "perfectHash mapping produced a non-empty out_ph.sam"; else bad "out_ph.sam missing/empty"; fi
mapped_ph="$(awk "$MAP_AWK" out_ph.sam)"
echo "       mapped alignment records (perfectHash index): ${mapped_ph}"
if [ "$mapped_ph" -ge 1 ]; then ok "perfectHash index also yields mapped alignments"; else bad "perfectHash index yielded none"; fi

# --- 5. the packaged helper script -----------------------------------------
# Upstream installs scripts/RunRapMap.sh into bin/ with a `#!/bin/bash` shebang,
# but HarmonyOS PC provides no /bin/bash (verified: [ -e /bin/bash ] fails while
# /usr/bin/env and /data/service/hnp/bin/bash both exist), so executing it would
# fail with ENOENT regardless of PATH.  Patch 0004 rewrites the shebang to
# `#!/usr/bin/env bash`, which is verified to work on the device; we therefore
# assert it really runs rather than merely asserting the executable bit.
helper="$(command -v RunRapMap.sh 2>/dev/null || true)"
if [ -n "$helper" ] && [ -x "$helper" ]; then
  ok "packaged RunRapMap.sh installed and executable"
  if "$helper" --version > helper.log 2>&1; then
    if grep -q '^rapmap' helper.log; then
      ok "RunRapMap.sh dispatches to the packaged rapmap binary ($(head -1 helper.log))"
    else
      bad "RunRapMap.sh ran but produced no rapmap banner: $(head -3 helper.log)"
    fi
  else
    bad "RunRapMap.sh failed to execute: $(head -3 helper.log)"
  fi
else
  bad "RunRapMap.sh not found on PATH"
fi

echo
echo "rapmap consumer test: ${pass} passed, ${fail} failed"
[ "$fail" -eq 0 ] || exit 1
exit 0
