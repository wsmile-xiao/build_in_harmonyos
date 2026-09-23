#!/data/service/hnp/bin/bash
# test_package/test.sh — end-to-end smoke test for LAST (last-align)
# Runs in conanrun env (PATH includes installed bin/).
# Exercises the core binaries on real sequence data:
#   lastdb (build index) -> lastal (align) -> verify output contains matches.
set -eu

base_dir="${TMPDIR:-.}"
workdir="$(mktemp -d "$base_dir/last-test.XXXXXX" 2>/dev/null || mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

echo "[test] lastdb --version"
lastdb --version

echo "[test] lastal --version"
lastal --version

echo "[test] last-split --version"
last-split --version

# Create a small reference and query FASTA with a shared motif.
cat > "$workdir/ref.fa" <<'EOF'
>ref1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
EOF

cat > "$workdir/query.fa" <<'EOF'
>query1
ACGTACGTACGTACGTACGTACGTACGT
EOF

echo "[test] lastdb build index"
lastdb -uNEAR "$workdir/ref" "$workdir/ref.fa"

echo "[test] lastal align query against reference"
lastal -fMAF "$workdir/ref" "$workdir/query.fa" > "$workdir/out.maf"

if ! grep -q "^a score=" "$workdir/out.maf"; then
    echo "❌ lastal produced no alignment"
    exit 1
fi

if ! grep -q "ref1" "$workdir/out.maf"; then
    echo "❌ alignment output missing reference sequence name"
    exit 1
fi

echo "✅ last-align end-to-end smoke test passed"
