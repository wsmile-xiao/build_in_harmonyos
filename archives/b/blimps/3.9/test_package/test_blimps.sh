#!/data/service/hnp/bin/bash
# Functional tests for the packaged blimps 3.9 tool suite.
#
# codehop and blimps outputs are compared against the upstream-distributed
# golden files (examples/*/distribution/ inside the 3.9 tarball); the only
# normalization is the absolute-path echo lines that depend on the directory
# the tools were invoked from.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FIX="$HERE/fixtures"
WORK="$PWD/blimps-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"

cleanup() {
    status=$?
    if [ "$status" -eq 0 ]; then
        rm -rf "$WORK"
    else
        echo "blimps functional test failed; preserving logs in $WORK" >&2
        find "$WORK" -maxdepth 2 -type f -print >&2 || true
    fi
}
trap cleanup EXIT

# --- codehop: degenerate PCR primer design; full output must match the ---
# --- upstream golden euk.out (input: euk.blks from examples/codehop)   ---
mkdir "$WORK/codehop"
cd "$WORK/codehop"
cp "$FIX/euk.blks" "$FIX/default.amino.frq" "$FIX/identity.frq" "$FIX/arab.codon.use" .
codehop euk.blks -Carab.codon.use -O3 > euk.out 2> euk.err
test -s euk.out
sed 's|codon usage table "arab.codon.use"|codon usage table "../../docs/arab.codon.use"|' \
    euk.out > euk.norm.out
diff -u "$FIX/euk.golden.out" euk.norm.out
echo "[test] codehop golden match: OK"

# --- blimps: sequence vs Blocks database search; full output must match ---
# --- the upstream golden example.bli (example.pro vs sample.blocks)     ---
mkdir "$WORK/search"
cd "$WORK/search"
cp "$FIX/example.pro" "$FIX/sample.blocks" "$FIX/default.amino.frq" "$FIX/default.qij" .
cat > example.cs <<'EOF'
ER    2
FR    default.amino.frq
SQ    example.pro
DB    sample.blocks
OU    example.bli
ST    2
RE    1
NU    0
CO    3
//
EOF
blimps example.cs > blimps.stdout 2> blimps.stderr
test -s example.bli
grep -Eq 'Records Searched:[[:space:]]+9' example.bli
norm_probe() { sed 's|^Probe File: .*|Probe File: TEST|' "$1"; }
norm_probe example.bli > example.norm.bli
norm_probe "$FIX/blimps.golden.bli" > golden.norm.bli
diff -u golden.norm.bli example.norm.bli
echo "[test] blimps search golden match: OK"

# --- blkprob: post-process the same search results ---
blkprob example.cs > example.blkprob 2> blkprob.stderr
test -s example.blkprob
grep -q 'Database=sample.blocks' example.blkprob
grep -q 'Query=' example.blkprob
echo "[test] blkprob: OK"

# --- motifj: Block Maker (motif algorithm) on the PROSITE lipoprotein ---
# --- example from examples/protomat                                   ---
mkdir "$WORK/motifj"
cd "$WORK/motifj"
cp "$FIX/lipo.pros" "$FIX/default.amino.frq" .
motifj 4 -lipo.pros < /dev/null > motifj.log 2>&1
test -s lipo.mot
test -s lipo.motifj.pros
echo "[test] motifj: OK"

echo "blimps functional test: PASS"
