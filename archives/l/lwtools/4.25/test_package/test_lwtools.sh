#!/bin/sh
# test_package functional tests for lwtools 4.25 (HarmonyOS PC / aarch64).
#
# Usage: sh test_lwtools.sh <package-bin-dir> <lwcc-basedir>
#
# Every assertion really executes an installed lwtools binary and checks its
# observable output (R34: no print-only tests).  POSIX sh only so the same
# script runs under toybox ash (device) and bash (CI worker).

BIN="$1"
LWCC_BASE="$2"

if [ -z "$BIN" ] || [ ! -d "$BIN" ]; then
    echo "not ok - binary directory argument missing or invalid"
    exit 1
fi
if [ -z "$LWCC_BASE" ] || [ ! -d "$LWCC_BASE" ]; then
    echo "not ok - lwcc base directory argument missing or invalid"
    exit 1
fi

# No `set -e` on purpose: every case below is a counted assertion, and an early
# abort would turn a single failure into a lost rest-of-suite result.
WORK=$(mktemp -d 2>/dev/null) || WORK="./lwtools-test.$$"
mkdir -p "$WORK"
cd "$WORK" || exit 1
# Keep an absolute cwd: the lwar extract assertion runs in a sub-shell.
WORK=$(pwd) || exit 1

pass=0
fail=0
ok()   { pass=$((pass + 1)); echo "ok - $1"; }
bad()  { fail=$((fail + 1)); echo "NOT OK - $1"; }

# $1 = name, $2 = expected first line of --version output
check_version() {
    _exe="$1"; _want="$2"
    if [ ! -f "$BIN/$_exe" ]; then
        bad "$_exe not installed"
        return
    fi
    _got=$("$BIN/$_exe" --version 2>&1 | head -n 1)
    if [ "$_got" = "$_want" ]; then
        ok "$_exe --version reports the packaged release"
    else
        bad "$_exe --version: got '$_got' want '$_want'"
    fi
}

# 1-6: all shipped programs carry the 4.25 banner
check_version lwasm     "lwasm from lwtools 4.25"
check_version lwlink    "lwlink from lwtools 4.25"
check_version lwar      "lwar from lwtools 4.25"
check_version lwcc      "lwcc from lwtools 4.25"
check_version lwcc-cpp  "lwcc-cpp from lwtools 4.25"
check_version lwcc-cc   "lwcc-cc from lwtools 4.25"

# 7: lwobjdump ships in bin/ (it has no --version banner; assertion 11 is the
# one that executes it on a real object file)
if [ -f "$BIN/lwobjdump" ]; then
    ok "lwobjdump installed"
else
    bad "lwobjdump missing from bin/"
fi

# Golden source: known-good 6809 encodings (verified against the upstream
# opcode table in test/tests/opcodes6809.pl).
cat > org.asm <<'EOF'
        org     $8000
start   ldx     #$4000
        pshs    x
        lda     #$12
        sta     0,x
        puls    x
        tfr     a,b
        nop
EOF

# 8: --raw output must equal the expected machine code byte-for-byte
if "$BIN/lwasm" --raw -o org.bin org.asm 2>raw.err; then
    GOT=$(od -An -tx1 org.bin 2>/dev/null | tr -d ' \n')
    if [ "$GOT" = "8e400034108612a70035101f8912" ]; then
        ok "lwasm --raw emits the expected 14 bytes of 6809 machine code"
    else
        bad "lwasm --raw bytes: got '$GOT' want '8e400034108612a70035101f8912'"
    fi
else
    bad "lwasm --raw failed: $(head -n 1 raw.err 2>/dev/null)"
fi

# 9-11: object file -> linker -> dumpable output
cat > sect.asm <<'EOF'
        section mytext
start   ldx     #$4000
        lda     #$12
        sta     0,x
        nop
        end
EOF
if "$BIN/lwasm" --obj -o sect.obj sect.asm 2>obj.err && [ -s sect.obj ]; then
    ok "lwasm --obj produces a linkable object"
    # 10: the linker resolves it and emits exactly the assembled code
    if "$BIN/lwlink" --raw -o linked.bin sect.obj 2>link.err; then
        GOT=$(od -An -tx1 linked.bin 2>/dev/null | tr -d ' \n')
        if [ "$GOT" = "8e40008612a70012" ]; then
            ok "lwlink --raw reproduces the section code bytes"
        else
            bad "lwlink output bytes: got '$GOT' want '8e40008612a70012'"
        fi
    else
        bad "lwlink failed: $(head -n 1 link.err 2>/dev/null)"
    fi
    # 11: lwobjdump reads the object and shows the section + code
    DUMP=$("$BIN/lwobjdump" sect.obj 2>&1)
    if echo "$DUMP" | grep -q "SECTION mytext" && \
       echo "$DUMP" | grep -q "8E40008612A70012"; then
        ok "lwobjdump disassembles the object section"
    else
        bad "lwobjdump output unexpected: $(echo "$DUMP" | head -n 2)"
    fi
else
    bad "lwasm --obj failed: $(head -n 1 obj.err 2>/dev/null)"
    bad "lwlink skipped (no object)"
    bad "lwobjdump skipped (no object)"
fi

# 12: linker map file records the section
if "$BIN/lwasm" --obj -o map.obj sect.asm >/dev/null 2>&1 && \
   "$BIN/lwlink" -m map.txt -o map.out map.obj >/dev/null 2>&1 && \
   grep -qi "mytext" map.txt 2>/dev/null; then
    ok "lwlink --map writes a map containing the linked section"
else
    bad "lwlink map output missing the section"
fi

# 13-15: lwar create / list / extract round trip.  Exactly three assertions are
# counted on every path, so a prerequisite failure cannot hide behind a skip.
if cp sect.obj member1.obj && cp sect.obj member2.obj && [ -s member1.obj ]; then
    M1=$(wc -c < member1.obj)
    M2=$(wc -c < member2.obj)
    SIZES=$((M1 + M2))
    if "$BIN/lwar" --create test.ar member1.obj member2.obj 2>ar.err; then
        ASIZE=$(wc -c < test.ar)
        if [ -s test.ar ] && [ "$ASIZE" -gt "$SIZES" ]; then
            ok "lwar --create stores both members in a non-empty archive"
        else
            bad "lwar --create archive too small: archive=$ASIZE members=$SIZES"
        fi
        LIST=$("$BIN/lwar" --list test.ar 2>&1)
        if echo "$LIST" | grep -q "member1.obj" && echo "$LIST" | grep -q "member2.obj"; then
            ok "lwar --list reports both archived members"
        else
            bad "lwar --list output unexpected: $(echo "$LIST" | head -n 2)"
        fi
        mkdir -p extracted
        if (cd extracted && "$BIN/lwar" --extract "$WORK/test.ar" member1.obj) 2>extract.err && \
           cmp -s extracted/member1.obj member1.obj; then
            ok "lwar --extract restores a member byte-for-byte"
        else
            bad "lwar --extract round trip: $(head -n 1 extract.err 2>/dev/null)"
        fi
    else
        bad "lwar --create failed: $(head -n 1 ar.err 2>/dev/null)"
        bad "lwar --list skipped (no archive)"
        bad "lwar --extract skipped (no archive)"
    fi
else
    bad "lwar --create skipped (member objects unavailable)"
    bad "lwar --list skipped (member objects unavailable)"
    bad "lwar --extract skipped (member objects unavailable)"
fi

# 16: assembler rejects an unknown opcode with a non-zero status
cat > bad.asm <<'EOF'
        org     $8000
        frob    #$01
EOF
if "$BIN/lwasm" --raw -o bad.bin bad.asm >/dev/null 2>&1; then
    bad "lwasm accepted an invalid opcode"
else
    ok "lwasm rejects an invalid opcode with a non-zero exit status"
fi

# 17: missing input file is reported, not silently ignored
ERR=$("$BIN/lwasm" -o nowhere.bin no-such-file.asm 2>&1)
RC=$?
if [ $RC -ne 0 ] && echo "$ERR" | grep -qi "no such file"; then
    ok "lwasm reports a missing input file"
else
    bad "lwasm missing-file behaviour: rc=$RC out='$ERR'"
fi

# 18-20: the C front end really preprocesses.  Assertion 18 calls lwcc-cpp
# directly and is the regression test for the packaged patch: without it the
# preprocessor dereferences an uncreated string list and dies with SIGSEGV
# (signal 11 / rc 139) for every input file — measured 10/10 on this device.
# Assertion 19 runs the same source through the lwcc driver, which locates its
# components from -B<base>/bin and, because HMDFS does not report the
# executable bit, from PATH.  Assertion 20 executes the driver component staged
# under lib/lwcc/bin/, i.e. it checks the driver-component install layout.
#
# The samples deliberately contain no macro *invocation*: upstream 4.25 still
# crashes intermittently while expanding object-like macros (measured 17/40 and
# 26/60 runs on this device when lwcc-cpp is called directly; 0/80 through the
# driver).  That is a separate upstream defect we do not patch, and asserting on
# it would make this suite non-deterministic.
printf 'int main(void) {\n    return 1;\n}\n' > plain.c
PATH="$BIN:$PATH"; export PATH
"$BIN/lwcc-cpp" -o cpp.i plain.c >cpp.out 2>cpp.err
RC=$?
if [ $RC -eq 0 ] && grep -q "return 1" cpp.i 2>/dev/null; then
    ok "lwcc-cpp preprocesses a source file instead of crashing (patched sysmacrolist)"
else
    bad "lwcc-cpp -o: rc=$RC err='$(head -n 1 cpp.err 2>/dev/null)' out='$(head -n 1 cpp.out 2>/dev/null)'"
fi
PP=$("$BIN/lwcc" "-B$LWCC_BASE" -E plain.c 2>/dev/null)
if echo "$PP" | grep -q "return 1"; then
    ok "lwcc -E preprocesses through the packaged lwcc-cpp"
else
    bad "lwcc -E output unexpected: $(echo "$PP" | head -n 2)"
fi
STAGED="$LWCC_BASE/lib/lwcc/bin/lwcc-cpp"
if [ -f "$STAGED" ] && "$STAGED" --version 2>&1 | grep -q "lwcc-cpp from lwtools 4.25"; then
    ok "the lwcc-cpp staged under lib/lwcc/bin runs (driver component layout)"
else
    bad "lib/lwcc/bin/lwcc-cpp missing or not runnable"
fi

cd /
rm -rf "$WORK"

total=$((pass + fail))
echo "1..$total"
echo "lwtools test_package: $pass/$total assertions passed, $fail failed"
[ "$fail" -eq 0 ]
