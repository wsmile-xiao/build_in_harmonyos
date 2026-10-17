#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for FastK executable
# Runs in conanrun env (PATH includes installed bin/).
set -euo pipefail

echo "[test] FastK (no args) prints usage"
out=$(FastK 2>&1 || true)
echo "$out" | grep -q "Usage: FastK" && echo "✅ FastK usage banner OK" || {
    echo "❌ FastK did not print usage banner"
    echo "$out"
    exit 1
}

echo "[test] FastK processes a synthetic FASTA"
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
cat > "$tmpdir/sample.fasta" << 'FASTA'
>seq1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>seq2
TTGGCCAATTGGCCAATTGGCCAATTGGCCAATTGGCCAATTGG
FASTA

# Run FastK with k=20 on the tiny sample.  FastK partitions the k-mer space
# into ~1024 shard files via simultaneous open() calls (split.c).  In a
# file-descriptor- or filesystem-restricted sandbox (e.g. CI worker with
# ulimit -n < 1024) this fails even though the binary is correct.
#
# Default: hard failure (R9/R34 — no fake pass).  Set FASTK_SKIP_FULL_RUN=1
# ONLY on sandboxes known to restrict fd allocation, and audit each use.
if FastK -k20 -T1 -N"$tmpdir/result" -P"$tmpdir" "$tmpdir/sample.fasta" >/dev/null 2>&1; then
    if [ -f "$tmpdir/result.hist" ]; then
        echo "✅ FastK produced .hist file"
    else
        echo "❌ FastK ran but .hist not found in $tmpdir:"
        ls -la "$tmpdir"
        exit 1
    fi
elif [ "${FASTK_SKIP_FULL_RUN:-0}" = "1" ]; then
    echo "⚠️  FastK full run skipped (FASTK_SKIP_FULL_RUN=1, sandbox fd limit)"
    echo "    usage banner test still passed — binary is executable"
else
    echo "❌ FastK failed to process the synthetic FASTA"
    exit 1
fi

echo "All tests passed."
