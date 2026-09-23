#!/bin/sh
# test_chordii.sh — chordii PostScript formatting + a2crd conversion test.
# Called by test_package/conanfile.py test() method.
#
# Args (passed by conanfile.py):
#   $1  res dir — contains the fixed fixture test.cho (ChordPro source).
#
# Scratch output files are created in a temp dir and removed, so nothing
# leaks into the source tree. Only POSIX tools are used.
set -eu

res_dir="${1:-}"
[ -n "${res_dir}" ] || { echo "FAIL: missing arg1 (res dir)"; exit 1; }
[ -f "${res_dir}/test.cho" ] || { echo "FAIL: fixture test.cho missing"; exit 1; }

work_dir="$(mktemp -d "${TMPDIR:-/tmp}/chordii_test_XXXXXX")" \
  || { echo "FAIL: cannot create work dir"; exit 1; }
trap 'rm -rf "$work_dir"' EXIT

# Test 1: chordii formats the fixture into PostScript.
chordii "${res_dir}/test.cho" -o "${work_dir}/out.ps" \
  || { echo "FAIL: chordii formatting failed"; exit 1; }
[ -s "${work_dir}/out.ps" ] || { echo "FAIL: empty PostScript output"; exit 1; }
head -1 "${work_dir}/out.ps" | grep -q "^%!PS" \
  || { echo "FAIL: output does not start with %!PS header"; exit 1; }
echo "PASS: PostScript output starts with %!PS header"

# Test 2: the formatted sheet embeds the song title from the fixture.
grep -q "Test Song" "${work_dir}/out.ps" \
  || { echo "FAIL: song title not found in PostScript output"; exit 1; }
echo "PASS: PostScript output contains the song title"

# Test 3: lyrics line reached the sheet.
grep -q "line of lyrics" "${work_dir}/out.ps" \
  || { echo "FAIL: lyric text not found in PostScript output"; exit 1; }
echo "PASS: PostScript output contains lyric text"

# Test 4: a2crd converts the fixture and keeps the chord directives.
a2crd "${res_dir}/test.cho" > "${work_dir}/out.crd" \
  || { echo "FAIL: a2crd conversion failed"; exit 1; }
[ -s "${work_dir}/out.crd" ] || { echo "FAIL: empty a2crd output"; exit 1; }
grep -q "Test \[C\]song" "${work_dir}/out.crd" \
  || { echo "FAIL: chord directives not preserved by a2crd"; exit 1; }
echo "PASS: a2crd conversion preserves chord directives"

echo "chordii consumer test: all 4 checks passed"
