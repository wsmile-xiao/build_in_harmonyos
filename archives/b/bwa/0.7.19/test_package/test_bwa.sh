#!/data/service/hnp/bin/bash
# Functional test for the packaged bwa binary.
set -euo pipefail

WORK="$PWD/bwa-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"

cleanup() {
    status=$?
    if [ "$status" -eq 0 ]; then
        rm -rf "$WORK"
    else
        echo "bwa functional test failed; preserving logs in $WORK" >&2
        find "$WORK" -maxdepth 1 -type f -print >&2 || true
    fi
}
trap cleanup EXIT

echo "[test] bwa usage"
bwa > "$WORK/usage.txt" 2>&1 || true
grep -q "Program: bwa" "$WORK/usage.txt"

cat > "$WORK/ref.fa" <<'EOF'
>ref
ACGTGCAATGTCAGTCAAGTCAGTTGACGATCGATCGTACGTAGCTAGCTAACGATCG
EOF

cat > "$WORK/read.fq" <<'EOF'
@r1
AGTCAAGTCAGTTGACGATCGATC
+
FFFFFFFFFFFFFFFFFFFFFFFF
EOF

echo "[test] bwa index"
bwa index "$WORK/ref.fa" > "$WORK/index.log" 2>&1
test -s "$WORK/ref.fa.bwt"
test -s "$WORK/ref.fa.pac"

echo "[test] bwa aln"
bwa aln "$WORK/ref.fa" "$WORK/read.fq" > "$WORK/read.sai" 2> "$WORK/aln.log"
test -s "$WORK/read.sai"

echo "[test] bwa samse"
bwa samse "$WORK/ref.fa" "$WORK/read.sai" "$WORK/read.fq" > "$WORK/aln.sam" 2> "$WORK/samse.log"

awk 'BEGIN { ok = 0 }
     $1 == "r1" && $2 == 0 && $3 == "ref" && $6 == "24M" { ok = 1 }
     END { exit ok ? 0 : 1 }' "$WORK/aln.sam"

echo "bwa functional test: PASS"
