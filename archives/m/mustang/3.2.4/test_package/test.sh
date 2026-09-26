#!/usr/bin/env bash
# test_package/test.sh — smoke test for the mustang executable.
# mustang has no --version; verify the banner and run a real alignment of two
# synthetic 20-residue polyalanine helices, asserting the FASTA output.
# Runs in conanrun env (PATH includes the installed bin/). The caller sets the
# cwd to the test build folder; every artifact is written there. Inputs are
# read from the script's own directory. No /tmp usage (read-only on target).
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

echo "[test] mustang --help banner check"
# capture to file first: pipefail + grep -q would SIGPIPE mustang mid-banner
mustang --help > banner.log 2>&1 || { echo "FAIL: --help exited nonzero"; exit 1; }
grep -q "MUSTANG" banner.log || { echo "FAIL: banner missing"; exit 1; }
echo "PASS: banner OK"

echo "[test] real 2-structure alignment (synthetic helices)"
cp "$here/a.pdb" "$here/b.pdb" .
mustang -i a.pdb b.pdb -F fasta -o t > run.log 2>&1
test -s t.afasta || { echo "FAIL: t.afasta missing or empty"; exit 1; }
grep -q ">a.pdb" t.afasta || { echo "FAIL: input label missing in t.afasta"; exit 1; }
grep -q "AAAAAAAAAAAAAAAAAAAA" t.afasta || { echo "FAIL: expected 20-residue sequence missing"; exit 1; }
echo "PASS: alignment produced expected FASTA"
