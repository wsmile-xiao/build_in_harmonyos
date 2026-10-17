#!/bin/sh
# test_idsgrep.sh — consumer functional test for the idsgrep 0.6 package.
# Runs the installed bin/idsgrep through real invocations and prints
# a machine-readable "RESULT: P passed, F failed" trailer line, which
# test_package/conanfile.py parses into HMBS_TEST_PACKAGE_RESULT.
# Every positive case asserts non-empty output plus exact expected content
# (toybox-tar lesson: never compare empty files against empty files).
# Negative controls: case 6 asserts a non-zero exit; case 5 asserts the
# missing-dictionary diagnostic text (2026-09-24 preflight proved idsgrep
# warns \"can't open ... for reading\" but still exits 0, so an exit-code
# gate would reject correct upstream behavior).
# Query shapes mirror upstream test/basicmatch and test/regex so the
# consumer test exercises proven upstream behavior against the
# OHOS-built binary.

set -u

BIN="${IDSGREP_BIN:-idsgrep}"
# Device /tmp may be read-only: prefer the HMBS-injected writable
# TMPDIR/TMP/TEMP, fall back to the current directory (never /tmp).
_TMPBASE="${TMPDIR:-${TMP:-${TEMP:-.}}}"
OUT="$_TMPBASE/idsgrep-test-out.txt"
PASS=0
FAIL=0

report() {
    # $1 = case number, $2 = ok (0/1), $3 = label
    if [ "$2" -eq 0 ]; then
        echo "CASE $1 PASS: $3"
        PASS=$((PASS + 1))
    else
        echo "CASE $1 FAIL: $3"
        FAIL=$((FAIL + 1))
    fi
}

dump_out() {
    # $1 = exit code; print bounded output excerpt for diagnosis.
    echo "  exit=$1, output excerpt (first 10 lines):"
    head -n 10 "$OUT" 2>/dev/null || echo "  (no output file)"
}

# Case 1: binary present, executable, non-empty.
if [ -x "$BIN" ] && [ -s "$BIN" ]; then
    report 1 0 "idsgrep binary present, executable and non-empty"
else
    report 1 1 "idsgrep binary missing/not-executable/empty: $BIN"
fi

# Case 2: -V prints a non-empty version banner mentioning 0.6.
"$BIN" -V > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && [ -s "$OUT" ] && grep -q "0\.6" "$OUT"; then
    report 2 0 "idsgrep -V reports version 0.6"
else
    dump_out $rc
    report 2 1 "idsgrep -V failed (exit=$rc, no 0.6 banner)"
fi

# Case 3: structural query on piped EIDS (upstream basicmatch shape).
printf '[g]hi[j]kl\n' | "$BIN" '[j]<k>;l' > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && printf '[j]kl\n' | diff - "$OUT" > /dev/null 2>&1; then
    report 3 0 "structural query '[j]<k>;l' matches '[j]kl'"
else
    dump_out $rc
    report 3 1 "structural query failed (exit=$rc)"
fi

# Case 4: PCRE regex query (upstream regex shape; proves PCRE linkage).
printf '<banana>;\n<bananana>[foo]xy\n' | "$BIN" '/<ana>;' > "$OUT" 2>&1
rc=$?
if [ $rc -eq 0 ] && printf '<banana>;\n<bananana>[foo]xy\n' | diff - "$OUT" > /dev/null 2>&1; then
    report 4 0 "PCRE query '/<ana>;' matches both entries"
else
    dump_out $rc
    report 4 1 "PCRE query failed (exit=$rc; PCRE linkage suspect)"
fi

# Case 5: missing dictionary file must print the upstream diagnostic.
# Upstream behavior (2026-09-24 preflight evidence): idsgrep prints
# \"can't open <path> for reading\" and exits 0, so the assertion is on
# the diagnostic text, not the exit code. Requiring the exact warning
# keeps this a real negative control (a stub binary would not emit it).
printf 'x\n' | "$BIN" '?' "$_TMPBASE/no-such-dict-missing.eids" > "$OUT" 2>&1
rc=$?
if grep -q "can't open" "$OUT" && grep -q "for reading" "$OUT"; then
    report 5 0 "missing dictionary diagnosed (exit=$rc)"
else
    dump_out $rc
    report 5 1 "missing dictionary diagnostic missing (exit=$rc)"
fi

# Case 6: unparsable query must fail with non-zero exit.
printf 'x\n' | "$BIN" 'u cant parse dis' > "$OUT" 2>&1
rc=$?
if [ $rc -ne 0 ]; then
    report 6 0 "unparsable query fails with exit=$rc"
else
    dump_out $rc
    report 6 1 "unparsable query unexpectedly succeeded"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
