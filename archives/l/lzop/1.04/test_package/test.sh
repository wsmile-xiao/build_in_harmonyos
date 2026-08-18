#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for the lzop executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
set -euo pipefail

# Test 1: binary executes and reports version
echo "[test] lzop --version"
lzop --version 2>&1 | grep -qi "lzop" || {
    echo "❌ lzop --version did not report lzop"
    exit 1
}
echo "✅ --version OK"

# Test 2: real compress → decompress round-trip with content verification
# NOTE: /tmp is read-only on OHOS — use $TMPDIR for the scratch dir.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/lzop-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# 8 KiB of repetitive (compressible) + random-ish payload
{
    seq 1 400 | sed 's/^/lzop round-trip line /'
    head -c 2048 /dev/urandom 2>/dev/null | od -An -tx1 | tr -d ' \n'
} > "$TESTDIR/input.bin" 2>/dev/null || true
wc -c < "$TESTDIR/input.bin" | grep -q '[1-9]' || {
    echo "❌ failed to create test input"
    exit 1
}

echo "[test] lzop -c (compress)"
lzop -c "$TESTDIR/input.bin" > "$TESTDIR/input.bin.lzo"
test -s "$TESTDIR/input.bin.lzo" || {
    echo "❌ lzop did not produce a compressed stream"
    exit 1
}
echo "✅ compressed OK ($(wc -c < "$TESTDIR/input.bin.lzo") bytes)"

echo "[test] lzop -dc (decompress) + content comparison"
lzop -dc "$TESTDIR/input.bin.lzo" > "$TESTDIR/output.bin"
cmp -s "$TESTDIR/input.bin" "$TESTDIR/output.bin" || {
    echo "❌ decompressed content differs from original"
    exit 1
}
echo "✅ round-trip content identical"
