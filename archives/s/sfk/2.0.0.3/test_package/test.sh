#!/bin/sh
# test_package/test.sh - consumer smoke test for the packaged sfk binary.
# Usage: test.sh <package-bin-dir>
# BINDIR (argv $1) is authoritative, resolved by test_package/conanfile.py
# from sfk's package_folder. Offline assertions only (no networking).
# Emits HMBS machine-evidence markers (hard gate).
#
# OHOS readonly_tmp hardening: /tmp on the device may be read-only (erofs),
# and some shells materialize $(...) in hardcoded /tmp. This script avoids
# $(...) / backticks; output capture uses plain redirection + grep.
set -eu

BINDIR="${1:-}"
if [ -z "$BINDIR" ] || [ ! -x "$BINDIR/sfk" ]; then
    echo "[test] FAIL: sfk binary not found in bindir '${BINDIR:-}'" >&2
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"sfk 2.0.0.3 ships no upstream test framework: Makefile.am defines only bin_PROGRAMS=sfk, with no TESTS/check_PROGRAMS target and no test directory; the mtk/ subtree is an optional tracing library, not a test harness.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":7,"passedCount":0}'
    exit 1
fi
SFK="$BINDIR/sfk"

# Resolve a writable temp dir (OHOS /tmp may be read-only).
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR TMP="$TMPDIR" TEMP="$TMPDIR" TEMPDIR="$TMPDIR"

PASS=0
FAIL=0

# check_grep <needle> <file> <message>
check_grep() {
    needle=$1
    file=$2
    message=$3
    if grep -Fq "$needle" "$file" 2>/dev/null; then
        echo "[test] PASS: $message"
        PASS=$((PASS+1))
    else
        echo "[test] FAIL: $message (missing '$needle')" >&2
        cat "$file" 2>/dev/null || true
        FAIL=$((FAIL+1))
    fi
}

# check_nonempty <file> <message>
check_nonempty() {
    file=$1
    message=$2
    if [ -s "$file" ]; then
        echo "[test] PASS: $message"
        PASS=$((PASS+1))
    else
        echo "[test] FAIL: $message (empty output)" >&2
        FAIL=$((FAIL+1))
    fi
}

workdir="$TMPDIR/sfk-test"
rm -rf "$workdir" 2>/dev/null || true
mkdir -p "$workdir"

# 1) Version banner: `sfk` with empty stdin prints the main help banner.
printf '' | "$SFK" > "$workdir/banner.txt" 2>&1 || true
check_grep "Release 2.0.0" "$workdir/banner.txt" "version banner reports Release 2.0.0"
check_grep "Revision 3" "$workdir/banner.txt" "version banner reports Revision 3"

# 2) calc: deterministic arithmetic.
"$SFK" calc 2+3 > "$workdir/calc.txt" 2>&1 || true
check_grep "5" "$workdir/calc.txt" "sfk calc 2+3 == 5"

# 3) mkdir: create a nested directory tree.
"$SFK" mkdir "$workdir/a/b/c" > "$workdir/mkdir.txt" 2>&1 || true
if [ -d "$workdir/a/b/c" ]; then
    echo "[test] PASS: sfk mkdir created nested directory"
    PASS=$((PASS+1))
else
    echo "[test] FAIL: sfk mkdir did not create nested directory" >&2
    FAIL=$((FAIL+1))
fi

# 4) md5: hash a known file (must equal standard md5 of 'hello world\n').
printf 'hello world\n' > "$workdir/data.txt"
"$SFK" md5 "$workdir/data.txt" > "$workdir/md5.txt" 2>&1 || true
check_grep "6f5902ac237024bdd0c176cb93063dc4" "$workdir/md5.txt" "sfk md5 matches known digest"

# 5) list: directory listing exposes the created file.
"$SFK" list "$workdir" > "$workdir/list.txt" 2>&1 || true
check_grep "data.txt" "$workdir/list.txt" "sfk list exposes created file"

# 6) time: emits a non-empty current timestamp.
"$SFK" time > "$workdir/time.txt" 2>&1 || true
check_nonempty "$workdir/time.txt" "sfk time emits a timestamp"

rm -rf "$workdir" 2>/dev/null || true

echo "[test] sfk consumer assertions: passed=$PASS failed=$FAIL"

# Upstream audit marker (authority: test_package/MANIFEST.yml).
echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"sfk 2.0.0.3 ships no upstream test framework: Makefile.am defines only bin_PROGRAMS=sfk, with no TESTS/check_PROGRAMS target and no test directory; the mtk/ subtree is an optional tracing library, not a test harness.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'

if [ "$FAIL" -eq 0 ] && [ "$PASS" -gt 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"/bin/sh test.sh\",\"discovered\":7,\"passedCount\":$PASS}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"/bin/sh test.sh\",\"discovered\":7,\"passedCount\":$PASS}"
    exit 1
fi
