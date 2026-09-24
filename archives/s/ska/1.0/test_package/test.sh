#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the ska executable (OHOS)
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
# New OHOS consumer case: end-to-end split-kmer workflow on OHOS.
set -euo pipefail

# OHOS /tmp is read-only — work inside the conan build folder instead.
WORKDIR="$(pwd)/ska-test-data"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

echo "[test] ska version"
ska version | grep -q "Version: 1.0"
echo "OK: ska version reports 1.0"

# --- Generate a pair of synthetic 2kb bacterial "genomes" (SNP divergence) ---
cat > gen_fa.py <<'PYEOF'
import random
random.seed(42)
s1 = ''.join(random.choice('ACGT') for _ in range(2000))
s2 = list(s1)
for pos in (300, 700, 1100, 1500):
    s2[pos] = {'A':'C','C':'G','G':'T','T':'A'}[s2[pos]]
with open('g1.fa', 'w') as f:
    f.write('>genome1\n' + '\n'.join(s1[i:i+70] for i in range(0, 2000, 70)) + '\n')
with open('g2.fa', 'w') as f:
    f.write('>genome2\n' + '\n'.join(''.join(s2)[i:i+70] for i in range(0, 2000, 70)) + '\n')
PYEOF
python3 gen_fa.py

echo "[test] ska fasta (create split kmer file from two fasta assemblies)"
ska fasta g1.fa g2.fa > fasta.log 2>&1
[ -s fasta.skf ] || { echo "FAIL: fasta.skf not created"; exit 1; }
echo "OK: fasta.skf created"

echo "[test] ska info (read back the split kmer file)"
ska info fasta.skf > info.log 2>&1
grep -q "Kmer size: 15" info.log || { echo "FAIL: kmer size mismatch"; exit 1; }
grep -Eq "Number of kmers: [1-9]" info.log || { echo "FAIL: no kmers stored"; exit 1; }
echo "OK: info reports nonzero kmers, k=15"

echo "[test] gzip input support (zlib linkage feasibility on OHOS)"
gzip -c g1.fa > g1.fa.gz
gzip -c g2.fa > g2.fa.gz
# Use a distinct output prefix (-o gz) so the assertion below cannot be
# satisfied by the uncompressed run's fasta.skf (P2 review fix).
ska fasta -o gz g1.fa.gz g2.fa.gz > gz.log 2>&1
[ -s gz.skf ] || { echo "FAIL: gz input did not produce gz.skf"; exit 1; }
ska info gz.skf > gz_info.log 2>&1
grep -Eq "Number of kmers: [1-9]" gz_info.log || { echo "FAIL: gz input produced no kmers"; exit 1; }
echo "OK: gzip-compressed fasta input works (gz.skf)"

echo "[test] ska distance (pairwise SNP distances + clustering)"
ska distance -o dist.tsv fasta.skf > dist.log 2>&1
[ -s dist.tsv.distances.tsv ] || { echo "FAIL: distances tsv missing"; exit 1; }
echo "OK: distance matrix written"
echo "ALL OK"
