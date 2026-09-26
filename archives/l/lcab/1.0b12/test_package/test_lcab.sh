#!/usr/bin/env bash
# test_package/test_lcab.sh — functional test for the lcab executable.
# Runs under conanrun env (PATH contains the installed bin/).
set -euo pipefail

tmp_root="${TMPDIR:-$HOME/tmp}"
mkdir -p "$tmp_root"
work="$(mktemp -d "$tmp_root/lcab-test-XXXXXX")"
trap 'rm -rf "$work"' EXIT
cd "$work"

fail() { echo "FAIL: $*" >&2; exit 1; }

# Search a binary cabinet for a literal string. Device grep (toybox) matches
# per line with C strings, so text after the first NUL byte of a line is never
# seen; split on NUL with the bash builtin instead.
cab_has() {
    local LC_ALL=C chunk
    while IFS= read -r -d '' chunk || [ -n "$chunk" ]; do
        [[ $chunk == *"$2"* ]] && return 0
    done < "$1"
    return 1
}

# --- 1. usage/version banner -------------------------------------------------
lcab -h > help.txt || fail "lcab -h returned $?"
grep -q "usage:" help.txt || fail "usage line missing"
grep -q "v1.0b12" help.txt || fail "version banner is not 1.0b12: $(tail -2 help.txt)"
echo "OK: usage banner reports v1.0b12"

# --- 2. single file cabinet --------------------------------------------------
printf 'hello harmony cabinet\n' > payload.txt
lcab -n payload.txt single.cab > /dev/null || fail "lcab -n failed"
[ -s single.cab ] || fail "single.cab is empty"
head -c 4 single.cab | grep -q "MSCF" || fail "cabinet magic MSCF missing"
cab_has single.cab "payload.txt" || fail "file name not stored in cabinet"
cab_has single.cab "hello harmony cabinet" || fail "file data not stored in cabinet"
echo "OK: single-file cabinet has MSCF header, file name and data"

# --- 3. multiple files, quiet mode -------------------------------------------
printf 'second file\n' > second.txt
lcab -n -q payload.txt second.txt multi.cab > quiet.log || fail "lcab -n -q failed"
head -c 4 multi.cab | grep -q "MSCF" || fail "multi.cab magic missing"
cab_has multi.cab "second.txt" || fail "second file not stored"
if grep -q "inputfiles" quiet.log; then fail "-q should not list input files"; fi
[ "$(wc -c < multi.cab)" -gt "$(wc -c < single.cab)" ] \
    || fail "multi-file cabinet is not larger than single-file cabinet"
echo "OK: multi-file cabinet built in quiet mode"

# --- 4. recursive directory mode ---------------------------------------------
mkdir -p tree/sub
printf 'nested payload\n' > tree/sub/nested.txt
lcab -r tree rec.cab > /dev/null || fail "lcab -r failed"
head -c 4 rec.cab | grep -q "MSCF" || fail "rec.cab magic missing"
cab_has rec.cab "nested payload" || fail "recursed file data missing"
echo "OK: recursive mode packed nested file"

# --- 5. missing input file is reported, not crashing -------------------------
if lcab -n does-not-exist.txt bad.cab > bad.log 2>&1; then
    grep -q "does-not-exist.txt" bad.log || fail "missing input not reported"
else
    fail "lcab crashed on missing input (rc=$?)"
fi
echo "OK: missing input handled gracefully"

echo "ALL LCAB TESTS PASSED"
