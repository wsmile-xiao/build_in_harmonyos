#!/bin/sh
# Consumer verification for magicrescue 1.1.10 (CLI tool).
# A real user scenario: recover a gzip file embedded in a disk-image blob
# using the installed `magicrescue` binary + the shipped `gzip` recipe,
# then verify the recovered payload content.
set -euo pipefail

TMPD=$(mktemp -d "${TMPDIR:-/tmp}/mr-consumer.XXXXXX") || exit 2
trap 'rm -rf "$TMPD"' EXIT INT TERM

# 1) Build a blob containing a gzip file with a recognizable payload
#    (payload must decompress to >= 100 bytes — magicrescue's default
#     min_output_file, otherwise the recovered file is dropped)
for i in $(seq 1 20); do
    printf 'magicrescue consumer test payload line %02d — verify recovery works.\n' "$i"
done > "$TMPD/payload.txt"
if command -v gzip >/dev/null 2>&1; then
    gzip -c "$TMPD/payload.txt" > "$TMPD/sample.gz"
else
    # Fallback: use python to write a minimal valid gzip stream
    python3 - "$TMPD/payload.txt" "$TMPD/sample.gz" <<'PY'
import gzip, sys
with open(sys.argv[1], 'rb') as fin, gzip.open(sys.argv[2], 'wb') as fout:
    fout.write(fin.read())
PY
fi
cp "$TMPD/sample.gz" "$TMPD/blob"

# 2) Locate the recipes shipped with the installed package (prefix/share/magicrescue/recipes)
MR_BIN=$(command -v magicrescue) || { echo "FAIL: magicrescue not in PATH"; exit 1; }
PREFIX=$(dirname "$(dirname "$MR_BIN")")
RECIPE_DIR="${RECIPE_DIR:-$PREFIX/share/magicrescue/recipes}"
[ -f "$RECIPE_DIR/gzip" ] || { echo "FAIL: gzip recipe missing: $RECIPE_DIR/gzip"; exit 1; }

# 3) Run magicrescue to recover the gzip file from the blob
mkdir -p "$TMPD/out"
if ! "$MR_BIN" -d "$TMPD/out" -r "$RECIPE_DIR/gzip" "$TMPD/blob" >/dev/null 2>&1; then
    echo "FAIL: magicrescue exited nonzero"
    exit 1
fi

# 4) Verify observable result: recovered (decompressed) payload content
if grep -q "consumer test payload" "$TMPD"/out/* 2>/dev/null; then
    echo "magicrescue consumer test: PASS (payload recovered and verified)"
    exit 0
else
    echo "FAIL: recovered file missing or wrong content"
    echo "--- out dir ---"; ls -la "$TMPD"/out/ 2>/dev/null
    exit 1
fi