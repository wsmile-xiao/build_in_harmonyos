#!/data/service/hnp/bin/bash
# test_bowtie2.sh — functional test for the bowtie2 read-aligner toolset.
# Runs in conanrun env (PATH includes installed bin/).
set -euo pipefail

# --------------------------------------------------------------------------
# Test 1: bowtie2-align-s --version — the small-index aligner binary.
# --------------------------------------------------------------------------
align_ver="$(bowtie2-align-s --version 2>&1)" || true
if echo "$align_ver" | grep -q "2.5.5"; then
    echo "PASS: bowtie2-align-s version 2.5.5"
else
    echo "FAIL: unexpected bowtie2-align-s version: $align_ver"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 2: bowtie2-build-s --version — the small-index builder binary.
# --------------------------------------------------------------------------
build_ver="$(bowtie2-build-s --version 2>&1)" || true
if echo "$build_ver" | grep -q "2.5.5"; then
    echo "PASS: bowtie2-build-s version 2.5.5"
else
    echo "FAIL: unexpected bowtie2-build-s version: $build_ver"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 3: bowtie2-inspect-s --version — the small-index inspector binary.
# --------------------------------------------------------------------------
inspect_ver="$(bowtie2-inspect-s --version 2>&1)" || true
if echo "$inspect_ver" | grep -q "2.5.5"; then
    echo "PASS: bowtie2-inspect-s version 2.5.5"
else
    echo "FAIL: unexpected bowtie2-inspect-s version: $inspect_ver"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 4: bowtie2-build-s builds a small index from a tiny FASTA reference.
# --------------------------------------------------------------------------
WORK="$(pwd)/bowtie2-testdata"
rm -rf "$WORK" && mkdir -p "$WORK"

cat > "$WORK/ref.fa" <<'EOF'
>ref1
ACGTACGTACGTACGTACGTACGTACGTACGTACGTACGT
>ref2
TTTTGGGGCCCCAAAATTTTGGGGCCCCAAAATTTTGGGG
EOF

bowtie2-build-s "$WORK/ref.fa" "$WORK/refidx" > "$WORK/build.log" 2>&1 || {
    echo "FAIL: bowtie2-build-s exited non-zero"
    cat "$WORK/build.log"
    exit 1
}

# A successful small-index build produces .bt2 files (1.bt2 .. 4.bt2 + rev).
if [ -f "$WORK/refidx.1.bt2" ]; then
    echo "PASS: bowtie2-build-s produced .1.bt2 index file"
else
    echo "FAIL: bowtie2-build-s did not produce .1.bt2 index file"
    ls -la "$WORK"
    exit 1
fi

# Verify the reverse-complement index too.
# bowtie2-build-s produces .rev.1.bt2 and .rev.2.bt2 (not .1.rev.bt2).
if [ -f "$WORK/refidx.rev.1.bt2" ]; then
    echo "PASS: bowtie2-build-s produced .rev.1.bt2 reverse index"
else
    echo "FAIL: bowtie2-build-s did not produce .rev.1.bt2 reverse index"
    ls -la "$WORK"
    exit 1
fi

echo "ALL TESTS PASSED"
