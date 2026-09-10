#!/data/service/hnp/bin/bash
# test_package/test_cldump.sh — smoke test for the packaged cldump binary.
# Really executes the installed binary (R34: the binary IS the API under test).
# --version/--help exit 0 before touching any database file, so no fixture is
# needed; the two negative cases pin distinct exit codes + stderr markers, so
# a stub binary (e.g. always exit 1) or empty-output fake cannot pass all 4.
set -u

BIN="cldump"
discovered=4
passed=0
failed=0

echo "[test] $BIN --version (prints version line, exit 0)"
VOUT=$("$BIN" --version 2>&1)
VRC=$?
echo "$VOUT"
if [ "$VRC" -eq 0 ] && echo "$VOUT" | grep -q "cldump v0.11"; then
    passed=$((passed + 1))
    echo "[OK] --version prints 'cldump v0.11'"
else
    failed=$((failed + 1))
    echo "[FAIL] --version rc=$VRC, expected 'cldump v0.11' in output"
fi

echo "[test] $BIN --help (prints usage, exit 0)"
HOUT=$("$BIN" --help 2>&1)
HRC=$?
echo "$HOUT" | head -n 8
if [ "$HRC" -eq 0 ] && echo "$HOUT" | grep -q "Usage:"; then
    passed=$((passed + 1))
    echo "[OK] --help prints 'Usage:'"
else
    failed=$((failed + 1))
    echo "[FAIL] --help rc=$HRC, expected 'Usage:' in output"
fi

echo "[test] $BIN with no file argument (must exit 3, 'no filename specified')"
NOUT=$("$BIN" 2>&1)
NRC=$?
echo "$NOUT" | head -n 5
if [ "$NRC" -eq 3 ] && echo "$NOUT" | grep -q "no filename specified"; then
    passed=$((passed + 1))
    echo "[OK] missing-file-argument path exits 3"
else
    failed=$((failed + 1))
    echo "[FAIL] no-arg rc=$NRC, expected 3 + 'no filename specified'"
fi

echo "[test] $BIN on a nonexistent file (must exit 1, \"Couldn't open file\")"
MOUT=$("$BIN" /nonexistent-cldump-test-0x5A.dat 2>&1)
MRC=$?
echo "$MOUT" | head -n 5
if [ "$MRC" -eq 1 ] && echo "$MOUT" | grep -q "Couldn't open file"; then
    passed=$((passed + 1))
    echo "[OK] nonexistent-file path exits 1"
else
    failed=$((failed + 1))
    echo "[FAIL] nonexistent-file rc=$MRC, expected 1 + \"Couldn't open file\""
fi

if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed/$discovered checks failed"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_cldump.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi

echo "OK: all $discovered checks passed"
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_cldump.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"make","command":"make check (n/a: no check target)","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,"reason":"cldump 0.11-dfsg upstream orig.tar.gz audited (12 src files, hand-written src/Makefile with only all/clean targets, no tests dir, no TESTS/check_PROGRAMS, no CTest/gtest/pytest; Debian packaging has no autopkgtest executables)"}\n'
exit 0
