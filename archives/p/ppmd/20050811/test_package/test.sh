#!/data/service/hnp/bin/bash
# test_package/test.sh — behaviour checks for the packaged ppmd executable.
#
# Invoked by test_package/conanfile.py inside the conanrun environment, so
# `ppmd` is the installed bin/ppmd. Every check drives the real CLI on real
# files and compares bytes/exit codes; no check is satisfied by the binary
# merely starting up.
#
# ppmd works on the current directory only: encode writes <base>.pmd next to
# the input, decode writes the archived name into the CWD, so every scenario
# runs with CWD=$WORK and bare file names.
#
# Exit codes of ppmd itself are part of the contract:
#   0   = success
#   255 = usage error / unreadable or corrupt archive (exit(-1))
#   139 = SIGSEGV — never acceptable

set -u

TMPBASE="${TMPDIR:-$HOME}"
WORK="$TMPBASE/ppmd-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

PASSED=0
FAILED=0

check() {
    # $1 description, $2 actual, $3 expected
    if [ "$2" = "$3" ]; then
        PASSED=$((PASSED + 1))
        printf 'ok   %s\n' "$1"
    else
        FAILED=$((FAILED + 1))
        printf 'FAIL %s\n     expected: [%s]\n     actual:   [%s]\n' "$1" "$3" "$2"
    fi
}

gen_corpus() {
    printf 'PPMd variant I round trip test on OpenHarmony aarch64.\n'
    for i in 1 2 3 4 5 6 7 8 9 10; do
        printf 'line %s the quick brown fox jumps over the lazy dog\n' "$i"
    done
}

# ---- 1. usage surface -------------------------------------------------------
ppmd --version >/dev/null 2>&1
check "--version exits 0" "$?" "0"
ppmd -h >/dev/null 2>&1
check "-h prints usage and exits 0" "$?" "0"
ppmd >/dev/null 2>&1
check "no-args usage exits 255" "$?" "255"
check "usage documents the e|d form" \
    "$(ppmd 2>&1 | grep -c 'e|d')" "1"

cd "$WORK" || exit 1

# ---- 2. text round trip, default parameters ---------------------------------
gen_corpus > text.txt
cp text.txt text.txt.ref
ppmd e -s text.txt >/dev/null 2>&1
check "encode exits 0" "$?" "0"
rm -f text.txt
ppmd d -s text.pmd >/dev/null 2>&1
check "decode exits 0" "$?" "0"
cmp -s text.txt.ref text.txt
check "text round trip is byte identical" "$?" "0"

# ---- 3. binary round trip ----------------------------------------------------
cp /bin/sh blob.bin
cp blob.bin blob.bin.ref
ppmd e -s blob.bin >/dev/null 2>&1
rm -f blob.bin
ppmd d -s blob.pmd >/dev/null 2>&1
cmp -s blob.bin.ref blob.bin
check "binary round trip is byte identical" "$?" "0"

# ---- 4. switch matrix round trips --------------------------------------------
for sw in "-o16 -m64" "-o2 -m1" "-r1 -o8" "-r2 -o4 -m32"; do
    gen_corpus > sw.txt
    cp sw.txt sw.txt.ref
    ppmd e $sw -s sw.txt >/dev/null 2>&1
    rm -f sw.txt
    ppmd d $sw -s sw.pmd >/dev/null 2>&1
    cmp -s sw.txt.ref sw.txt
    check "round trip with switches [$sw]" "$?" "0"
done

# ---- 5. canonical ppmdi1 archive header --------------------------------------
gen_corpus > hdr.txt
ppmd e -s hdr.txt >/dev/null 2>&1
check "archive magic is PPMd signature 84ACAF8F little endian" \
    "$(head -c 4 hdr.pmd | od -A n -t x1 | tr -d ' \n')" "8fafac84"
check "archive stores the original file name at offset 16" \
    "$(dd if=hdr.pmd bs=1 skip=16 count=7 2>/dev/null)" "hdr.txt"
check "compressed archive is smaller than the text input" \
    "$([ "$(stat -c %s hdr.pmd)" -lt "$(stat -c %s hdr.txt)" ] && echo yes || echo no)" "yes"

# ---- 6. non-silent statistics line -------------------------------------------
gen_corpus > stats.txt
stats_out="$(ppmd e stats.txt 2>&1)"
check "non-silent encode reports the bpb statistics line" \
    "$(printf '%s\n' "$stats_out" | grep -c 'bpb')" "1"

# ---- 7. -f custom archive name ------------------------------------------------
gen_corpus > custom.txt
cp custom.txt custom.txt.ref
ppmd e -s -fcustom.arc custom.txt >/dev/null 2>&1
check "-f writes the archive under the requested name" \
    "$([ -f custom.arc ] && echo yes)" "yes"
rm -f custom.txt
ppmd d -s custom.arc >/dev/null 2>&1
cmp -s custom.txt.ref custom.txt
check "archive made with -f decodes byte identical" "$?" "0"

# ---- 8. -d deletes inputs after encoding --------------------------------------
gen_corpus > del.txt
ppmd e -s -d del.txt >/dev/null 2>&1
check "-d removes the input file after encoding" \
    "$([ -f del.txt ] && echo present || echo deleted)" "deleted"

# ---- 9. wildcards --------------------------------------------------------------
rm -f ./*.pmd
gen_corpus > w1.txt
gen_corpus > w2.txt
ppmd e -s '*.txt' >/dev/null 2>&1
check "wildcard encodes both matching files" \
    "$([ -f w1.pmd ] && [ -f w2.pmd ] && echo both)" "both"

# ---- 10. corrupt archives are rejected gracefully ------------------------------
printf 'this is not a ppmd archive at all........' > junk.pmd
ppmd d -s junk.pmd >/dev/null 2>&1
JUNK_RC=$?
check "decoding a junk file exits non-zero" \
    "$([ "$JUNK_RC" -ne 0 ] && echo yes)" "yes"
check "junk decode does not crash with SIGSEGV" \
    "$([ "$JUNK_RC" -eq 139 ] && echo crashed || echo ok)" "ok"

head -c 10 w1.pmd > trunc.pmd
ppmd d -s trunc.pmd >/dev/null 2>&1
TRUNC_RC=$?
check "decoding a truncated archive does not crash with SIGSEGV" \
    "$([ "$TRUNC_RC" -eq 139 ] && echo crashed || echo ok)" "ok"

printf '================================================================\n'
printf 'TOTAL: %d  PASS: %d  FAIL: %d\n' "$((PASSED + FAILED))" "$PASSED" "$FAILED"
[ "$FAILED" -eq 0 ]
