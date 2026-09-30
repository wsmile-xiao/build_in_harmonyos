#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the installed `mlucas` executable.
#
# Runs the exact invocation used by upstream's own `tests/spot-check` check target
# (shipped in the official release tarball) and verifies the deterministic result.
set -eu

echo "[test] installed mlucas: $(command -v mlucas)"

echo "[test] mlucas -fftlen 192 -iters 100 -radset 0   (upstream spot-check)"
out="$(mlucas -fftlen 192 -iters 100 -radset 0 2>&1)"
printf '%s\n' "$out" | tail -25

# M3888509 @ 192K FFT, 100 iterations: deterministic reference residue.
printf '%s\n' "$out" | grep -q 'M3888509' || {
    echo "❌ expected self-test on M3888509 (FFT length 192K)" >&2
    exit 1
}
printf '%s\n' "$out" | grep -q 'Res64: 71E61322CCFB396C' || {
    echo "❌ unexpected Res64 residue (computation mismatch)" >&2
    exit 1
}
printf '%s\n' "$out" | grep -q 'Done \.\.\.' || {
    echo "❌ spot-check did not run to completion" >&2
    exit 1
}

echo "✅ mlucas spot-check OK (M3888509, Res64 71E61322CCFB396C)"
