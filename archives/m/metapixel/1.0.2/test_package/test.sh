#!/bin/sh
# test.sh - metapixel 1.0.2 consumer test (L0c test source, R34).
#
# Really drives the packaged binaries through metapixel's public workflow and
# asserts on real artifacts.  The prepared library is deliberately mixed
# PNG + JPEG + GIF so that all three rwimg backends - and therefore both
# API-compat patches - are exercised by the decode step.
#
# The fixtures are generated at run time by gen_images.py rather than shipped
# as files: the CI worker checks out a PR as a text .diff, and GitCode's diff
# endpoint carries no binary payload, so a committed .png would break the
# whole checkout.  PNG and GIF are written from scratch with the standard
# library only; the JPEG fixture is an embedded base64 constant with a pinned
# SHA256.
#
# usage: sh test.sh <metapixel> <metapixel-imagesize> <convert> <gen_images.py>
# exit:   0 = all assertions passed, 1 = assertion failure, 2 = usage error
set -u

METAPIXEL="$1"
IMAGESIZE="$2"
CONVERT="$3"
GENIMAGES="$4"

[ -n "$METAPIXEL" ] && [ -n "$IMAGESIZE" ] && [ -n "$CONVERT" ] && [ -n "$GENIMAGES" ] || {
	echo "usage: $0 <metapixel> <metapixel-imagesize> <convert> <gen_images.py>"
	exit 2
}
[ -x "$METAPIXEL" ] || { echo "FAIL: not executable: $METAPIXEL"; exit 2; }
[ -x "$IMAGESIZE" ] || { echo "FAIL: not executable: $IMAGESIZE"; exit 2; }
[ -f "$GENIMAGES" ] || { echo "FAIL: generator missing: $GENIMAGES"; exit 2; }

# R10: never hardcode /tmp - on OHOS it is read-only.
WORK="${TMPDIR:-$HOME/tmp}/metapixel-test.$$"
LIB="$WORK/library"
IMAGES="$WORK/images"
rm -rf "$WORK"
mkdir -p "$LIB" || { echo "FAIL: cannot create $LIB"; exit 2; }
trap 'rm -rf "$WORK"' EXIT

# T0 materialise the fixtures.  gen_images.py verifies its own output (magic
# bytes, minimum size, and the JPEG digest), so a broken generator fails here
# rather than quietly weakening the assertions below.
if ! python3 "$GENIMAGES" "$IMAGES"; then
	echo "FAIL: could not generate test fixtures"
	exit 1
fi

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
ko() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1"; }

# TILE_W/TILE_H are deliberately 8x8 so a 64x64 source splits into 64 cells
# and the tiny 5-tile library can still fill it once tile reuse is allowed.
TILE_W=8
TILE_H=8
TABLES="$LIB/tables.mxt"
SRC="$IMAGES/target.png"
OUT_PNG="$WORK/mosaic.png"
OUT_JPG="$WORK/mosaic.jpg"

echo "--- metapixel 1.0.2 test_package ---"

# ---------------------------------------------------------------- T0
if [ -s "$IMAGES/target.png" ] && [ -s "$IMAGES/tile_c.gif" ] && [ -s "$IMAGES/tile_d.jpg" ]; then
	ok "T0 test fixtures generated (target.png + PNG/JPEG/GIF tiles)"
else
	ko "T0 test fixtures missing under $IMAGES"
fi

# ---------------------------------------------------------------- T1
out=$("$METAPIXEL" --version 2>&1)
case "$out" in
*"metapixel 1.0.2"*) ok "T1 --version reports metapixel 1.0.2" ;;
*) ko "T1 --version unexpected: $out" ;;
esac

# ---------------------------------------------------------------- T2
out=$("$METAPIXEL" --help 2>&1)
if printf '%s\n' "$out" | grep -q -- "--metapixel" &&
   printf '%s\n' "$out" | grep -q -- "--library" &&
   printf '%s\n' "$out" | grep -q -- "--prepare"; then
	ok "T2 --help documents --library/--prepare/--metapixel"
else
	ko "T2 --help did not document the main subcommands"
fi

# ---------------------------------------------------------------- T3
out=$("$METAPIXEL" --print-prepare-settings 2>&1)
w=$(printf '%s\n' "$out" | awk '{print $1}')
h=$(printf '%s\n' "$out" | awk '{print $2}')
if [ -n "$w" ] && [ -n "$h" ] && [ "$w" -gt 0 ] 2>/dev/null && [ "$h" -gt 0 ] 2>/dev/null; then
	ok "T3 --print-prepare-settings reports a positive tile size ($w x $h)"
else
	ko "T3 --print-prepare-settings unexpected: $out"
fi

# ------------------------------------------- T4..T6  decode, one per backend
# Each --prepare call decodes the source image, scales it to the tile size and
# appends its matching coefficients to the library table.  A failure here means
# that format backend cannot read its input at all.
for spec in "png:T4 PNG decode" "jpg:T5 JPEG decode" "gif:T6 GIF decode"; do
	ext=${spec%%:*}
	label=${spec#*:}
	src=""
	for cand in "$IMAGES"/tile_*."$ext"; do
		[ -f "$cand" ] && src="$cand" && break
	done
	if [ -z "$src" ]; then
		ko "$label - no .$ext input found in $IMAGES"
		continue
	fi
	stem=$(basename "$src")
	stem=${stem%.*}
	if "$METAPIXEL" -w "$TILE_W" -h "$TILE_H" --prepare \
		"$src" "$LIB/$stem" "$TABLES" >/dev/null 2>&1 &&
		[ -s "$LIB/$stem" ]; then
		ok "$label - --prepare produced library entry $stem"
	else
		ko "$label - --prepare failed for $stem"
	fi
done

# ---------------------------------------------------------------- T7
[ -s "$TABLES" ] && ok "T7 library table tables.mxt was written" ||
	ko "T7 library table tables.mxt missing or empty"

# ---------------------------------------------------------------- T8
# -d 0 allows a constituent image to be reused; with 5 tiles and 64 cells the
# default minimum distance of 1 would legitimately fail with
# "cannot find a matching image".
if "$METAPIXEL" -w "$TILE_W" -h "$TILE_H" -d 0 --library "$LIB" \
	--metapixel "$SRC" "$OUT_PNG" >/dev/null 2>&1 && [ -s "$OUT_PNG" ]; then
	ok "T8 classic photomosaic written to PNG"
else
	ko "T8 classic photomosaic to PNG failed"
fi

# ---------------------------------------------------------------- T9
# Round-trip the artifact through the delivered reader: a correct
# png_set_IHDR() (patch 0002) is what makes the dimensions come back.
sz=$("$IMAGESIZE" "$OUT_PNG" 2>/dev/null)
if [ "$sz" = "64 64" ]; then
	ok "T9 mosaic.png decodes as 64x64 via metapixel-imagesize"
else
	ko "T9 metapixel-imagesize on mosaic.png returned '$sz', expected '64 64'"
fi

# ---------------------------------------------------------------- T10
if [ -s "$OUT_PNG" ] && [ "$(dd if="$OUT_PNG" bs=1 count=8 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "89504e470d0a1a0a" ]; then
	ok "T10 mosaic.png carries a valid PNG signature"
else
	ko "T10 mosaic.png is not a valid PNG"
fi

# ---------------------------------------------------------------- T11
if "$METAPIXEL" -w "$TILE_W" -h "$TILE_H" -d 0 --library "$LIB" \
	--metapixel "$SRC" "$OUT_JPG" >/dev/null 2>&1 && [ -s "$OUT_JPG" ]; then
	ok "T11 classic photomosaic written to JPEG"
else
	ko "T11 classic photomosaic to JPEG failed"
fi

# ---------------------------------------------------------------- T12
sz=$("$IMAGESIZE" "$OUT_JPG" 2>/dev/null)
if [ "$sz" = "64 64" ]; then
	ok "T12 mosaic.jpg decodes as 64x64 via metapixel-imagesize"
else
	ko "T12 metapixel-imagesize on mosaic.jpg returned '$sz', expected '64 64'"
fi

# ---------------------------------------------------------------- T13
# Collage mode: arbitrary rectangle placement rather than a matrix.
COLLAGE="$WORK/collage.png"
if "$METAPIXEL" -w "$TILE_W" -h "$TILE_H" -d 0 --library "$LIB" --collage \
	--metapixel "$SRC" "$COLLAGE" >/dev/null 2>&1 && [ -s "$COLLAGE" ] &&
	[ "$("$IMAGESIZE" "$COLLAGE" 2>/dev/null)" = "64 64" ]; then
	ok "T13 --collage mosaic written and decodes as 64x64"
else
	ko "T13 --collage mosaic failed"
fi

# ---------------------------------------------------------------- T14
# The other matching metric must reach the same conclusion.
WAVE="$WORK/wavelet.png"
if "$METAPIXEL" -w "$TILE_W" -h "$TILE_H" -d 0 -m wavelet --library "$LIB" \
	--metapixel "$SRC" "$WAVE" >/dev/null 2>&1 && [ -s "$WAVE" ]; then
	ok "T14 -m wavelet metric produced a mosaic"
else
	ko "T14 -m wavelet metric failed"
fi

# ---------------------------------------------------------------- T15
# convert reads a lisp configuration on stdin and re-emits the constituent
# image data.  Assert on the *shape* of that output: the banner, the
# small-image record, and a positive pixel size.
conv_out=$(printf '(small-image "tile" (size 32 24))\n' | "$CONVERT" 2>&1)
size_field=$(printf '%s\n' "$conv_out" | sed -n 's/.*(size \([0-9][0-9]*\) \([0-9][0-9]*\)).*/\1 \2/p' | head -1)
sw=$(printf '%s' "$size_field" | awk '{print $1}')
sh_=$(printf '%s' "$size_field" | awk '{print $2}')
if printf '%s\n' "$conv_out" | grep -q '; -\*- lisp -\*-' &&
   printf '%s\n' "$conv_out" | grep -q 'small-image' &&
   printf '%s\n' "$conv_out" | grep -q 'subpixel' &&
   [ -n "$sw" ] && [ "$sw" -gt 0 ] 2>/dev/null && [ -n "$sh_" ] && [ "$sh_" -gt 0 ] 2>/dev/null; then
	ok "T15 convert emitted a small-image record with a positive size ($size_field)"
else
	ko "T15 convert produced unexpected output: $conv_out"
fi

# ---------------------------------------------------------------- T16
# T15 alone would also pass for a program that ignores stdin and prints a
# fixed template, so pin the input dependency down: two different
# configurations must produce two different outputs, and the same
# configuration must be reproducible.  A stub that ignores stdin, or one
# carrying uninitialised memory into its output, fails one of these.
conv_a=$(printf '(small-image "alpha" (size 32 24))\n' | "$CONVERT" 2>&1)
conv_b=$(printf '(small-image "bravo" (size 16 16))\n' | "$CONVERT" 2>&1)
conv_a2=$(printf '(small-image "alpha" (size 32 24))\n' | "$CONVERT" 2>&1)
if [ "$conv_a" != "$conv_b" ] && [ "$conv_a" = "$conv_a2" ] &&
   [ -n "$conv_a" ] && [ -n "$conv_b" ]; then
	ok "T16 convert output depends on its input and is reproducible"
else
	ko "T16 convert output is not input-dependent or not reproducible"
fi

echo "METAPIXEL_TEST_SUMMARY total=$((PASS + FAIL)) passed=$PASS failed=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
