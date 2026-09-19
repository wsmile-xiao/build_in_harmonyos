#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer functional test for the toppred executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# TOPPREDDATA must point at the packaged share/toppred scales (set by
# test_package/conanfile.py — the compiled-in pkgdatadir is stale after
# conan's DESTDIR-staged install).  /tmp is read-only on OHOS — use
# $HOME/tmp for scratch.
set -euo pipefail

: "${TOPPREDDATA:?TOPPREDDATA must point at the packaged share/toppred}"
export TOPPREDDATA

SCRATCH="${TMPDIR:-$HOME/tmp}/toppred-test-$$"
mkdir -p "$SCRATCH"
trap 'rm -rf "$SCRATCH"' EXIT

cat > "$SCRATCH/mini.fasta" <<'EOF'
>mini_seq window size (default) equal to sequence length
VAKLFADAIIIIITSFISPYT
EOF

echo "[test] toppred predicts transmembrane topology (upstream min_seqlen case)"
toppred -g none -t none "$SCRATCH/mini.fasta" > "$SCRATCH/out.txt" 2> "$SCRATCH/err.txt"

grep -q "Found: 1 segments" "$SCRATCH/out.txt" || {
    echo "FAIL: expected exactly 1 predicted segment"
    cat "$SCRATCH/out.txt" "$SCRATCH/err.txt"
    exit 1
}
grep -qE "TRANSMEM[[:space:]]+1[[:space:]]+21[[:space:]]+21" "$SCRATCH/out.txt" || {
    echo "FAIL: expected TRANSMEM segment spanning residues 1-21"
    cat "$SCRATCH/out.txt"
    exit 1
}
echo "OK: 1 transmembrane segment predicted (residues 1-21, Certain)"

echo "[test] toppred loads packaged hydrophobicity scales (upstream hydro case)"
for scale in GES-scale KD-scale GVH-scale; do
    toppred -g none -t none -H "$scale" -o "$SCRATCH/hyd.out" "$SCRATCH/mini.fasta" > /dev/null
    grep -q "Using hydrophobicity file: $scale" "$SCRATCH/hyd.out" || {
        echo "FAIL: hydrophobicity scale $scale was not used"
        cat "$SCRATCH/hyd.out"
        exit 1
    }
done
echo "OK: all packaged hydrophobicity scales load and apply"

echo "ALL CONSUMER TESTS PASSED"
