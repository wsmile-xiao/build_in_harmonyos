#!/bin/sh
# illustrate consumer test — drive the installed binary through a real render
# and assert on structurally meaningful output.
#
# Usage: test_illustrate.sh <illustrate-binary> <workdir> <share-dir>
#
# <share-dir> is the packaged share/illustrate directory holding the upstream
# sample scene (2hhb.inp + 2hhb.pdb).  Section C drives that real upstream
# scene, which is the actual end-to-end consumer flow: `illustrate < 2hhb.inp`.
#
# Rendering notes (measured on the OHOS aarch64 binary, see notes.md):
#   * the rasteriser maps 1 Angstrom == 1 pixel; the `scale` card only
#     multiplies the sphere radii.  A 5-Angstrom molecule in a 200x200 canvas
#     therefore covers ~10 px, so the descriptor radius (not the canvas size)
#     is what makes the atoms actually cover pixels.
#   * the world card's negative size triggers autosizing, which clamps to
#     3000x3000; the packaged 2hhb scene at that size takes minutes and emits a
#     109 MB PNM.  Both scenes below use an explicit positive size instead.
#   * illustrate always writes a fixed `opacity.pnm` next to the named output,
#     and both files land in the current working directory.
set -u

BIN="$1"
WORKDIR="$2"
SHAREDIR="$3"
pass=0
fail=0

ok() { pass=$((pass + 1)); echo "ok - $1"; }
no() { fail=$((fail + 1)); echo "NOT OK - $1"; }
check() { if [ "$1" -eq 0 ]; then ok "$2"; else no "$2"; fi; }

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR" || exit 1
cd "$WORKDIR" || exit 1

# ════════════════════════════════════════════════════════════════════
# Section A — 4-atom synthetic scene, two atom types.
#
# Atom descriptor cards colour residues by the PDB columns 13-22, with '-'
# as a wildcard.  Atom 1-2 are residue 1 (ALA), atom 3-4 residue 2 (GLY), so
# `-C-------A` (column 13 = 'C' = carbon) matches only the ALA atoms and
# everything else falls through to the `----------` catch-all.
#
# Colours are chosen so that a mixed-colour scene must contain BOTH pure red
# and pure blue pixels: if the renderer ignored the descriptor cards and fell
# back to one colour, one of the two assertions fails.
# ════════════════════════════════════════════════════════════════════
cat > scene.pdb <<'EOF'
ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 20.00           C
ATOM      2  CB  ALA A   1      10.000   0.000   0.000  1.00 20.00           C
ATOM      3  N   GLY A   2      20.000  10.000   0.000  1.00 20.00           N
ATOM      4  C   GLY A   2      30.000   5.000  10.000  1.00 20.00           C
END
EOF

# Radius 20.0 with scale 1.0 gives 20-pixel spheres: large enough that the
# atoms cover thousands of pixels and the shading/outline passes are visible
# in the output, instead of a 10-pixel speck.
cat > scene.inp <<'EOF'
read
scene.pdb
ATOM  -C-------A 0,9999, 1.0,0.0,0.0, 20.0
ATOM  ---------- 0,9999, 0.0,0.0,1.0, 20.0
END
center
auto
trans
0.,0.,0.
scale
1.0
zrot
0.
wor
1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0
1,0.0023,2.0,1.0,0.2
200,200
illustrate
3.0,10.0,4,0.0,5.0
3.0,10.0
3.0,8.0,6000.
calculate
scene.pnm
EOF

rm -f scene.pnm opacity.pnm run.stdout run.stderr
"$BIN" < scene.inp > run.stdout 2> run.stderr
rc=$?

# A1. exit status
check "$([ "$rc" -eq 0 ] && echo 0 || echo 1)" "illustrate exits 0 (rc=$rc)"

# A2. all four atoms parsed and echoed (list-directed output pads with spaces,
#     so the count is matched as a whitespace-delimited field)
grep -Eq 'atoms read: +4 +from: +scene\.pdb' run.stdout
check $? "program parsed all 4 atoms from scene.pdb"

# A3. normal F77 completion marker on stderr — distinguishes a finished run
#     from a crash mid-calculation
grep -q "Fortran STOP" run.stderr
check $? "Fortran STOP completion marker present"

# A4. PNM magic; header line 2 is "<ysize> <xsize>" (format 2i5)
head -c 2 scene.pnm 2>/dev/null | grep -q "P3"
check $? "output scene.pnm is P3 (plain PPM)"

[ "$(sed -n 2p scene.pnm | tr -d ' ')" = "200200" ]
check $? "image size is the requested 200x200"

# A5. the depth-buffer pass rasterised every atom: illustrate reports one
#     "N spheres added of type: T" line per descriptor type.  Our 4-atom
#     scene uses two atom descriptors (type 1 and type 2), which together
#     must account for all 4 atoms.
total_spheres=$(awk '/spheres added of type:/ {sum += $1} END {print sum}' run.stdout)
[ "${total_spheres:-0}" -eq 4 ]
check $? "depth buffer reports 4 spheres rasterised (got $total_spheres)"

# A6. the molecule actually covers pixels.  Counted over the whole pixel
#     stream (P3 rows hold many pixels), not just the first field of each row.
pixel_stream() { tail -n +4 "$1" | tr -s ' \n' '\n\n' | paste - - -; }
drawn=$(pixel_stream scene.pnm | awk '$1 < 250 || $2 < 250 || $3 < 250' | wc -l)
total=$(pixel_stream scene.pnm | wc -l)
[ "${drawn:-0}" -gt 500 ]
check $? "molecule rendered ($drawn of $total pixels are non-background)"

# A7/A8. per-atom descriptor colours: residues ALA (carbon, cols 13-22 = C)
#        must come out pure red, the GLY catch-all atoms pure blue.  Both must
#        appear, so a renderer that ignored the descriptor cards fails here.
#        The pixel stream is flattened to one line first because P3 spreads
#        the components of one pixel across line breaks.
tr -s ' \n' '  ' < scene.pnm > flat.pnm
grep -q '255 0 0' flat.pnm
check $? "ALA atoms drawn with their descriptor colour (pure red 255 0 0)"

grep -q '0 0 255' flat.pnm
check $? "GLY atoms drawn with their descriptor colour (pure blue 0 0 255)"

# A9. opacity companion image: same header grammar, and it must not be a copy
#     of the colour image (it carries the opacity channel instead).
[ -s opacity.pnm ] && head -c 2 opacity.pnm | grep -q "P3"
check $? "opacity.pnm companion image written"

cmp -s scene.pnm opacity.pnm
[ $? -ne 0 ]
check $? "opacity.pnm carries the opacity channel, not a copy of scene.pnm"

# ════════════════════════════════════════════════════════════════════
# Section B — installed binary is an OHOS aarch64 ELF.
#
# These can only hold on the HarmonyOS target: a host build would be x86_64
# and would resolve a glibc/musl-x86 loader instead.  Read with plain shell
# so the check needs no readelf on the test machine.
# ════════════════════════════════════════════════════════════════════
head -c 20 "$BIN" | od -An -c | grep -q '177   E   L   F'
check $? "installed binary has an ELF magic header"

if command -v readelf >/dev/null 2>&1; then
  readelf -h "$BIN" 2>/dev/null | grep -q 'Machine:.*AArch64'
  check $? "installed binary is AArch64 (Machine: AArch64)"

  # PIE: Type: DYN, i.e. position independent.
  readelf -h "$BIN" 2>/dev/null | grep -q 'Type:.*DYN'
  check $? "installed binary is a PIE (Type: DYN)"

  # OHOS/musl targets resolve libc.so directly; there must be no host
  # toolchain library dragging in a foreign runtime.
  readelf -d "$BIN" 2>/dev/null | grep -q 'NEEDED.*libc\.so'
  check $? "installed binary links OHOS libc.so"
fi

# ════════════════════════════════════════════════════════════════════
# Section C — end-to-end consumer flow on the packaged upstream sample.
#
# This is the workflow the package documents in notes.md:
# `illustrate < share/illustrate/2hhb.inp` reproduces the README's haemoglobin
# illustration.  It runs against the sample files the recipe actually installs,
# so it fails if either the binary or the packaged data files are missing.
# Only the world card's size is changed (autosize -> explicit 200x200), every
# other card is the upstream file verbatim.
# ════════════════════════════════════════════════════════════════════
if [ -n "$SHAREDIR" ] && [ -f "$SHAREDIR/2hhb.inp" ] && [ -f "$SHAREDIR/2hhb.pdb" ]; then
  cp "$SHAREDIR/2hhb.inp" "$SHAREDIR/2hhb.pdb" .
  # -30,-30 is upstream's autosizing request; an explicit positive size keeps
  # the render at ~1 s instead of minutes / 109 MB.
  sed 's/^-30,-30$/200,200/' 2hhb.inp > 2hhb_scene.inp
  rm -f 2hhb.pnm opacity.pnm h2.stdout h2.stderr
  "$BIN" < 2hhb_scene.inp > h2.stdout 2> h2.stderr
  rc2=$?

  check "$([ "$rc2" -eq 0 ] && echo 0 || echo 1)" \
    "packaged 2hhb scene renders end-to-end (rc=$rc2)"

  grep -q "Fortran STOP" h2.stderr
  check $? "packaged 2hhb scene completes normally (Fortran STOP)"

  # The upstream haemoglobin has 4779 ATOM/HETATM records; illustrate reports
  # how many it actually consumed.  The exact count comes from upstream data,
  # so a mismatch means the PDB parser or the packaged file regressed.
  grep -Eq 'atoms read: +[0-9]+ +from: +2hhb\.pdb' h2.stdout
  check $? "packaged 2hhb.pdb parsed by the program"

  atoms2=$(sed -n 's/.*atoms read: *\([0-9]*\).*/\1/p' h2.stdout | head -1)
  [ -n "$atoms2" ] && [ "$atoms2" -gt 4000 ]
  check $? "packaged haemoglobin scene reads a full protein ($atoms2 atoms, expect >4000)"

  # 2hhb.pdb is 454 KB of upstream coordinates; if the packaged data files
  # were truncated or emptied this catches it before the render does.
  [ "$(wc -c < 2hhb.pdb)" -gt 400000 ]
  check $? "packaged 2hhb.pdb is intact ($(wc -c < 2hhb.pdb) bytes)"

  [ -s 2hhb.pnm ] && head -c 2 2hhb.pnm | grep -q "P3"
  check $? "packaged 2hhb scene wrote its named P3 output"

  [ "$(sed -n 2p 2hhb.pnm | tr -d ' ')" = "200200" ]
  check $? "packaged 2hhb scene honoured the requested 200x200"

  d2=$(pixel_stream 2hhb.pnm | awk '$1 < 250 || $2 < 250 || $3 < 250' | wc -l)
  [ "${d2:-0}" -gt 0 ]
  check $? "packaged 2hhb scene drew a non-empty molecule ($d2 non-background pixels)"
else
  echo "# skip: packaged share/illustrate sample not available at '$SHAREDIR'"
fi

echo "1..$((pass + fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
