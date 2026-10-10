#!/bin/sh
# illustrate consumer test — render a real scene and assert on real outputs.
#
# Usage: test_illustrate.sh <illustrate-binary> <workdir>
#
# The scene follows the command-card grammar from the upstream README and
# the shipped 2hhb.inp sample (read/center/trans/scale/zrot/wor/illustrate/
# calculate), but uses a four-atom PDB and an explicit 200x200 pixel size:
# illustrate's autosizing clamps to a 3000x3000 canvas which takes minutes
# under emulation, while an explicit positive size renders in about a
# second everywhere.  The program writes the named PNM plus a fixed
# opacity.pnm into the current working directory, so the script runs inside
# <workdir>.
set -u

BIN="$1"
WORKDIR="$2"
pass=0
fail=0

ok() { pass=$((pass+1)); echo "ok - $1"; }
no() { fail=$((fail+1)); echo "NOT OK - $1"; }

cd "$WORKDIR" || exit 1

# Four-atom scene; PDB atom records are fixed-column (element symbol in
# columns 77-78, coordinates in columns 31-54).
cat > scene.pdb <<'EOF'
ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 20.00           C
ATOM      2  CB  ALA A   1       1.520   0.000   0.000  1.00 20.00           C
ATOM      3  N   GLY A   2       2.900   1.200   0.500  1.00 20.00           N
ATOM      4  C   GLY A   2       4.100   0.600   1.100  1.00 20.00           C
END
EOF

# Command cards mirroring the upstream 2hhb.inp sample, with the
# world-resolution card set to an explicit 200,200 (see header comment).
cat > scene.inp <<'EOF'
read
scene.pdb
ATOM  ---------- 0,9999, 1.0,0.6,0.6, 1.6
END
center
auto
trans
0.,0.,0.
scale
10.0
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

# 1. exit status
if [ "$rc" -eq 0 ]; then
  ok "illustrate exits 0 (rc=$rc)"
else
  no "illustrate exited rc=$rc"
fi

# 2. all four atoms were parsed and echoed (list-directed output pads with
#    spaces, so match the count as a whitespace-delimited field)
if grep -Eq 'atoms read: +4 +from' run.stdout; then
  ok "program parsed all 4 atoms from scene.pdb"
else
  no "atom count line missing/wrong in run.stdout"
fi

# 3. normal F77 completion marker on stderr
if grep -q "Fortran STOP" run.stderr; then
  ok "Fortran STOP completion marker present"
else
  no "Fortran STOP marker missing (run did not complete normally)"
fi

# 4. PNM magic
if head -c 2 scene.pnm | grep -q "P3"; then
  ok "output scene.pnm is P3 (plain PPM)"
else
  no "scene.pnm is not a P3 PNM"
fi

# 5. requested dimensions honored (header line 2 is "<ysize> <xsize>",
#    written with 2i5 formatting)
if [ "$(sed -n 2p scene.pnm | tr -d ' ')" = "200200" ]; then
  ok "image size is the requested 200x200"
else
  no "unexpected image size: $(sed -n 2p scene.pnm)"
fi

# 6. molecule is actually drawn: at least one pixel channel below the
#    255 background level (header lines P3 / size / maxval skipped)
drawn=$(awk 'NR>3{for(i=1;i<=NF;i++) if($i<200){found=1}} END{print found+0}' scene.pnm)
if [ "$drawn" -eq 1 ]; then
  ok "non-background pixels present (molecule rendered)"
else
  no "image is entirely background — nothing was drawn"
fi

# 7. opacity companion image also written (always emitted alongside the
#    named output, same header grammar)
if [ -s opacity.pnm ] && head -c 2 opacity.pnm | grep -q "P3"; then
  ok "opacity.pnm companion image written"
else
  no "opacity.pnm missing or not P3"
fi

echo "1..$((pass+fail))"
echo "# passed: $pass"
echo "# failed: $fail"
[ "$fail" -eq 0 ] || exit 1
exit 0
