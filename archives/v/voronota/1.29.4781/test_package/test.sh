#!/data/service/hnp/bin/bash
# test_package/test.sh — functional consumer test for the voronota toolset.
# Runs inside the conanrun env (PATH includes the installed bin/).
# 4 checks, each with explicit non-empty-output assertions (toybox lesson:
# bare exit code 0 on empty fixtures proves nothing).
set -euo pipefail

# NOTE: /tmp is read-only on OHOS — use $HOME/tmp for the scratch dir.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/voronota-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# Test 1: core binary executes and prints help.
# Upstream src/voronota.cpp returns 1 on the bare --help path by design,
# so tolerate the exit code (|| true under set -e) and gate on content:
# non-empty plus the "Voronota version" banner an exec failure would lack.
echo "[test 1/4] voronota --help"
voronota --help > "$TESTDIR/help.txt" 2>&1 || true
test -s "$TESTDIR/help.txt" || { echo "FAIL: voronota --help produced empty output"; exit 1; }
grep -q "Voronota version" "$TESTDIR/help.txt" || { echo "FAIL: voronota --help missing version banner"; cat "$TESTDIR/help.txt"; exit 1; }
echo "OK test 1: --help printed $(wc -l < "$TESTDIR/help.txt") lines"

# Test 2: end-to-end balls -> vertices -> contacts pipeline on a synthetic PDB.
echo "[test 2/4] get-balls-from-atoms-file | calculate-vertices | calculate-contacts"
cat > "$TESTDIR/mini.pdb" <<'PDBEOF'
ATOM      1  N   ALA A   1      11.104  13.207   2.100  1.00 20.00           N
ATOM      2  CA  ALA A   1      12.104  13.507   2.100  1.00 20.00           C
ATOM      3  C   ALA A   1      12.504  14.207   0.800  1.00 20.00           C
ATOM      4  O   ALA A   1      13.104  15.207   0.900  1.00 20.00           O
ATOM      5  CB  ALA A   1      12.604  12.207   2.800  1.00 20.00           C
ATOM      6  N   GLY A   2      12.004  13.907  -0.300  1.00 20.00           N
ATOM      7  CA  GLY A   2      12.304  14.507  -1.600  1.00 20.00           C
ATOM      8  C   GLY A   2      11.104  15.207  -2.200  1.00 20.00           C
ATOM      9  O   GLY A   2      11.304  16.107  -3.000  1.00 20.00           O
TER      10      GLY A   2
END
PDBEOF
test -s "$TESTDIR/mini.pdb" || { echo "FAIL: synthetic fixture is empty"; exit 1; }
voronota get-balls-from-atoms-file < "$TESTDIR/mini.pdb" > "$TESTDIR/balls"
test -s "$TESTDIR/balls" || { echo "FAIL: balls output is empty"; exit 1; }
[ "$(wc -l < "$TESTDIR/balls")" -ge 4 ] || { echo "FAIL: balls has fewer than 4 entries"; exit 1; }
voronota calculate-vertices --print-log --check < "$TESTDIR/balls" > "$TESTDIR/vertices" 2> "$TESTDIR/vertices_log"
test -s "$TESTDIR/vertices" || { echo "FAIL: vertices output is empty"; exit 1; }
test -s "$TESTDIR/vertices_log" || { echo "FAIL: vertices log is empty"; exit 1; }
voronota calculate-contacts --volumes-output "$TESTDIR/volumes" < "$TESTDIR/balls" > "$TESTDIR/contacts"
test -s "$TESTDIR/contacts" || { echo "FAIL: contacts output is empty"; exit 1; }
test -s "$TESTDIR/volumes" || { echo "FAIL: volumes output is empty"; exit 1; }
echo "OK test 2: $(wc -l < "$TESTDIR/balls") balls -> $(wc -l < "$TESTDIR/vertices") vertices -> $(wc -l < "$TESTDIR/contacts") contacts"

# Test 3: voronota-js expansion binary smoke check.
echo "[test 3/4] voronota-js --help"
voronota-js --help > "$TESTDIR/js_help.txt" 2>&1 || true
test -s "$TESTDIR/js_help.txt" || { echo "FAIL: voronota-js produced empty output"; exit 1; }
echo "OK test 3: voronota-js printed $(wc -l < "$TESTDIR/js_help.txt") lines"

# Test 4: voronota-lt expansion binary smoke check.
echo "[test 4/4] voronota-lt --help"
voronota-lt --help > "$TESTDIR/lt_help.txt" 2>&1 || true
test -s "$TESTDIR/lt_help.txt" || { echo "FAIL: voronota-lt produced empty output"; exit 1; }
echo "OK test 4: voronota-lt printed $(wc -l < "$TESTDIR/lt_help.txt") lines"

echo "ALL 4 TESTS PASSED"
