#!/usr/bin/env bash
# test_package/test.sh — smoke test for the mkhexgrid executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

MKHEXGRID="${MKHEXGRID:-mkhexgrid}"
TMPDIR_LOCAL="${TMPDIR_LOCAL:-$(pwd)/tmp}"
mkdir -p "$TMPDIR_LOCAL"

# ─── Test 1: --version ───────────────────────────────────────
echo "[test] mkhexgrid --version"
OUTPUT=$("$MKHEXGRID" --version 2>&1) || exit 1
echo "$OUTPUT"
echo "$OUTPUT" | grep -q "mkhexgrid version 0.1.1"
echo "OK: --version returns mkhexgrid version 0.1.1"

# ─── Test 2: SVG output (no gd runtime dependency) ──────────
# SVG is pure text — best choice for a headless OHOS test environment.
echo "[test] mkhexgrid SVG grid generation"
SVGFILE="$TMPDIR_LOCAL/grid.svg"
"$MKHEXGRID" --hex-side=20 --columns=4 --rows=4 \
             --image-width=200 --image-height=200 \
             --output=svg \
             -o "$SVGFILE" || exit 1

# Verify the SVG file was created and is non-empty
if [ ! -s "$SVGFILE" ]; then
    echo "FAIL: SVG output file is empty or missing"
    exit 1
fi

# Verify SVG content markers
if ! grep -q '<svg' "$SVGFILE"; then
    echo "FAIL: SVG output missing <svg> root element"
    exit 1
fi
if ! grep -q '<?xml' "$SVGFILE"; then
    echo "FAIL: SVG output missing XML declaration"
    exit 1
fi

# Show a snippet of the output
head -5 "$SVGFILE"
LINES=$(wc -l < "$SVGFILE")
echo "OK: generated SVG grid ($LINES lines, $(wc -c < "$SVGFILE") bytes)"

# ─── Test 3: SVG to stdout via specfile + outfile '-' ───────
echo "[test] mkhexgrid specfile -> stdout (SVG)"
SPECFILE="$TMPDIR_LOCAL/spec.txt"
cat > "$SPECFILE" <<'EOF'
hex-side = 15
columns = 3
rows = 2
image-width = 120
image-height = 80
output = svg
EOF

STDOUTOUT=$("$MKHEXGRID" "$SPECFILE" -) || exit 1
if [ -z "$STDOUTOUT" ]; then
    echo "FAIL: no SVG output to stdout"
    exit 1
fi
echo "$STDOUTOUT" | grep -q '<svg'
echo "OK: specfile-mode SVG to stdout ($(echo "$STDOUTOUT" | wc -l) lines)"

echo "=== All tests passed ==="
