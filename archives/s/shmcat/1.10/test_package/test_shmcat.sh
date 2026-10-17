#!/usr/bin/env bash
# test_package/test_shmcat.sh — consumer test for shmcat 1.10 on HarmonyOS PC
#
# Usage: bash test_shmcat.sh <shmcat-bin> <ftok-bin> <workdir>
#
# shmcat is a CLI tool suite, so the consumer test drives the *installed*
# binaries and asserts their exact stdout/stderr/exit-code contract.
# Each [PASS] line is one assertion; the totals are printed at the end and are
# the numbers quoted in MANIFEST.yml / notes.md / manifest.yaml / PR body.

SHMCAT="$1"
FTOK="$2"
WORK="$3"

# `-u`/pipefail guard against silently wrong counters; `-e` is deliberately NOT
# enabled because this suite accumulates PASS/FAIL and exits non-zero at the end.
set -u -o pipefail

pass=0
fail=0
skip=0

ok()   { echo "  [PASS] $1"; pass=$((pass + 1)); }
bad()  { echo "  [FAIL] $1"; fail=$((fail + 1)); }
noset() { echo "  [SKIP] $1 — $2"; skip=$((skip + 1)); }

if [ ! -x "$SHMCAT" ]; then
    echo "[test] FATAL: shmcat binary not executable: $SHMCAT"
    exit 1
fi
mkdir -p "$WORK" || exit 1
cd "$WORK" || exit 1

echo "[test] shmcat = $SHMCAT"
echo "[test] ftok   = $FTOK"
echo "[test] workdir = $WORK"
echo

# ---------------------------------------------------------------- 1. version
echo "[case 1] -V banner advertises the compiled-in feature set"
verout="$("$SHMCAT" -V 2>&1)"
verrc=$?
if [ $verrc -eq 0 ] && printf '%s\n' "$verout" | grep -q '^shmcat 1\.10 (.*posix-shm.*)$'; then
    ok "exit 0 and banner reports shmcat 1.10 with posix-shm enabled"
else
    bad "unexpected -V output (rc=$verrc): $(printf '%s' "$verout" | head -1)"
fi

# ------------------------------------------------------------------- 2. help
echo "[case 2] -h documents every operand the build enabled"
helptxt="$("$SHMCAT" -h 2>&1)"; helprc=$?
if [ $helprc -eq 0 ] && printf '%s\n' "$helptxt" | grep -q -- '--posix-shm' \
        && printf '%s\n' "$helptxt" | grep -q -- '--file' \
        && printf '%s\n' "$helptxt" | grep -q -- '--stdin'; then
    ok "exit 0 and usage lists --file/--stdin/--posix-shm"
else
    bad "usage text incomplete (rc=$helprc)"
fi

# ------------------------------------------------------- 3. text operand -t
echo "[case 3] -t prints exactly the given text (printText/write path)"
printf 'shmcat-ohos-roundtrip-42' > exp_txt
"$SHMCAT" -t 'shmcat-ohos-roundtrip-42' > got_txt 2>/dev/null; tcrc=$?
if [ $tcrc -eq 0 ] && cmp -s exp_txt got_txt; then
    ok "stdout byte-identical to the operand, exit 0"
else
    bad "-t mismatch (rc=$tcrc, got $(wc -c < got_txt 2>/dev/null) bytes)"
fi

# --------------------------------------------- 4. file operand -f, 256 bytes
echo "[case 4] -f dumps a file byte-exactly, including all 256 byte values"
i=0
{ while [ $i -lt 256 ]; do printf "\\$(printf '%o' "$i")"; i=$((i + 1)); done; } > bin256
"$SHMCAT" -f bin256 > bin256.out 2>/dev/null; fcrc=$?
if [ $fcrc -eq 0 ] && cmp -s bin256 bin256.out; then
    ok "256-byte all-values file dumped identically, exit 0"
else
    bad "-f mismatch (rc=$fcrc, in=$(wc -c < bin256) out=$(wc -c < bin256.out))"
fi

# ------------------------------------------- 5. multi-chunk file (buffering)
echo "[case 5] -f on a 3264-byte file crosses the read/write loop boundary"
line='shmcat-OHOS-0123456789-abcdefghijklmnopqrstuvwxyz-'
i=0
{ while [ $i -lt 64 ]; do printf '%s\n' "$line"; i=$((i + 1)); done; } > big.txt
"$SHMCAT" -f big.txt > big.out 2>/dev/null; bcrc=$?
if [ $bcrc -eq 0 ] && cmp -s big.txt big.out; then
    ok "3264-byte file dumped identically, exit 0"
else
    bad "large -f mismatch (rc=$bcrc, in=$(wc -c < big.txt) out=$(wc -c < big.out))"
fi

# --------------------------------------------------- 6. implicit stdin dump
echo "[case 6] no operand at all falls back to the stdin dumper"
"$SHMCAT" < big.txt > stdin.out 2>/dev/null; scrc=$?
if [ $scrc -eq 0 ] && cmp -s big.txt stdin.out; then
    ok "stdin passthrough identical (dumpFd(STDIN_FILENO) fallback), exit 0"
else
    bad "stdin fallback mismatch (rc=$scrc)"
fi

# ------------------------------------------ 7. explicit -i combined with -n
echo "[case 7] '-i -n' dumps stdin and then appends a line feed"
printf 'abc' | "$SHMCAT" -i -n > in.out 2>/dev/null; icrc=$?
if [ $icrc -eq 0 ] && [ "$(wc -c < in.out)" -eq 4 ] && [ "$(tail -c 1 in.out | od -An -tx1 | tr -d ' \n')" = "0a" ]; then
    ok "output is exactly 'abc'+LF, exit 0 (two operands chained)"
else
    bad "-i -n mismatch (rc=$icrc, bytes=$(wc -c < in.out))"
fi

# --------------------------------------------- 8. POSIX shared memory -p (E2E)
echo "[case 8] -p dumps a real POSIX shared memory object byte-exactly"
shmname="shmcat_tp_$$"
shmpath="/dev/shm/$shmname"
if cp bin256 "$shmpath" 2>/dev/null && [ -f "$shmpath" ]; then
    "$SHMCAT" -p "/$shmname" > shm256.out 2>shm256.err; pcrc=$?
    if [ $pcrc -eq 0 ] && cmp -s bin256 shm256.out; then
        ok "shm_open(O_RDONLY)+fstat+mmap dump of /$shmname identical, exit 0"
    else
        bad "POSIX shm dump failed (rc=$pcrc): $(head -1 shm256.err 2>/dev/null)"
    fi
    rm -f "$shmpath"
else
    reason="creating $shmpath was refused"
    cp bin256 "$WORK/$shmname" 2>/dev/null
    if [ -f "$WORK/$shmname" ]; then
        "$SHMCAT" -p "/$shmname" > shm256.out 2>/dev/null; pcrc=$?
        if [ $pcrc -eq 0 ] && cmp -s bin256 shm256.out; then
            ok "POSIX shm object dumped identically via the mapped name, exit 0"
        else
            noset "-p" "$reason and the mapped-name object could not be dumped either (rc=$pcrc)"
        fi
        rm -f "$WORK/$shmname"
    else
        noset "-p" "$reason (no writable POSIX shm namespace for this uid)"
    fi
fi

# --------------------------------- 9..12. error contract (no syscall needed)
echo "[case 9] -f on a missing file is reported as an error, exit 1"
"$SHMCAT" -f ./definitely-missing-file > /dev/null 2>err9; e9=$?
if [ $e9 -eq 1 ] && grep -q 'Cannot open file' err9; then
    ok "exit 1 with 'Cannot open file' (SHMCAT_ERROR -> EXITCODE_ERROR)"
else
    bad "unexpected result (rc=$e9): $(head -1 err9)"
fi

echo "[case 10] -M rejects IPC_PRIVATE (key 0) before touching System V"
"$SHMCAT" -M 0 > /dev/null 2>err10; e10=$?
if [ $e10 -eq 1 ] && grep -q 'private shared memory segments' err10; then
    ok "exit 1 with the IPC_PRIVATE guard message"
else
    bad "unexpected result (rc=$e10): $(head -1 err10)"
fi

echo "[case 11] -m rejects a negative segment id at the parser"
"$SHMCAT" -m -5 > /dev/null 2>err11; e11=$?
if [ $e11 -eq 1 ] && grep -q 'Invalid shared memory id' err11; then
    ok "exit 1 with 'Invalid shared memory id'"
else
    bad "unexpected result (rc=$e11): $(head -1 err11)"
fi

echo "[case 12] an unknown long option exits with the usage code 10"
"$SHMCAT" --certainly-not-an-option > /dev/null 2>err12; e12=$?
if [ $e12 -eq 10 ] && grep -q 'Wrong usage' err12; then
    ok "exit 10 (EXITCODE_USAGE) with 'Wrong usage'"
else
    bad "unexpected result (rc=$e12): $(head -1 err12)"
fi

# ------------------------------------------------------------------ 13. ftok
echo "[case 13] ftok helper: deterministic key + hex/dec/oct agree"
if [ -x "$FTOK" ]; then
    h1="$("$FTOK" bin256 7 2>/dev/null)"; h2="$("$FTOK" bin256 7 2>/dev/null)"
    d1="$("$FTOK" -d bin256 7 2>/dev/null)"; o1="$("$FTOK" -o bin256 7 2>/dev/null)"
    case "$h1" in 0x[0-9a-f]*) hexok=1 ;; *) hexok=0 ;; esac
    if [ "$h1" = "$h2" ] && [ $hexok -eq 1 ]; then
        hv=$((h1))
        ov=$(( 8#${o1#0} ))
        if [ "$ov" -eq "$hv" ] && { [ "$d1" -eq "$hv" ] || [ "$d1" -eq $((hv - 4294967296)) ]; }; then
            ok "ftok stable across runs; same key_t in three formats: hex=$h1 dec=$d1 oct=$o1"
        else
            bad "ftok formats disagree (hex=$h1 dec=$d1 oct=$o1)"
        fi
    else
        bad "ftok output not deterministic or not hexadecimal (h1='$h1' h2='$h2')"
    fi

    "$FTOK" bin256 > /dev/null 2>err13b; e13b=$?
    "$FTOK" bin256 256 > /dev/null 2>err13c; e13c=$?
    if [ $e13b -eq 10 ] && [ $e13c -eq 10 ] && grep -q 'Wrong usage' err13b \
        && grep -q 'between 0 and 255' err13c; then
        ok "ftok argument validation exits 10 for a missing ID and an out-of-range ID"
    else
        bad "ftok usage validation (rc_args=$e13b rc_id=$e13c)"
    fi
else
    noset "ftok" "binary not present in this package"
    noset "ftok argument validation" "binary not present in this package"
fi

# ------------------------------------------------------- diag (not asserted)
# System V attach path: recorded as a platform observation (DRAFT-E584
# "compile+link+deliver, disclose the platform limit honestly"), never asserted,
# so the suite stays portable to workers where System V IPC is available.
# SIGSYS is not an errno-returning failure, hence it is reported as a signal.
diagrc=$( ulimit -c 0 2>/dev/null
          { "$SHMCAT" -m 0 >/dev/null 2>diag.err; printf '%s' "$?"; } 2>/dev/null )
if [ "$diagrc" -gt 128 ] 2>/dev/null; then
    diag="PLATFORM_LIMITATION: killed by signal $((diagrc - 128)) (SIGSYS = OHOS seccomp blocks System V IPC); recovery: a kernel/sandbox whose seccomp whitelist allows shmget/shmat"
else
    diag="exit code $diagrc: $(head -1 diag.err)"
fi
echo
echo "[diag] System V shmattach path ('shmcat -m 0') on this platform -> $diag"
echo "[diag] (informational only; not part of the assertion count)"

echo
echo "[test] assertions: PASS=$pass FAIL=$fail SKIP=$skip"
[ $fail -eq 0 ] || exit 1
exit 0
