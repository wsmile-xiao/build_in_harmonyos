#!/bin/sh
# test_package/test.sh — HarmonyOS consumer test suite for secpwgen 1.3.
# Usage: test.sh [bindir]
#
# BINDIR (argv $1) is authoritative: resolved by test_package/conanfile.py
# from the secpwgen package_folder, so the suite fails loudly if the package
# stops shipping bin/secpwgen (CI L1e destructive reverse check).
#
# OHOS readonly_tmp hardening: /tmp on the device is read-only (erofs) and
# /bin/sh materializes $(...) command substitution in hardcoded /tmp
# (ignoring TMPDIR), so this script contains ZERO $(...) / backticks.
# Output is captured with plain redirections into $TMPDIR files and asserted
# with grep/cmp.
#
# Upstream test audit: secpwgen 1.3 ships NO upstream test framework — the
# tarball's only Makefile (Makefile.proto) declares `all install-strip
# install clean` and no check/test target, and there is no test/tests
# directory (see test_package/MANIFEST.yml).  All 13 cases below are NEW.
#
# Case inventory (13 independent check items):
#   F1-F10  functional coverage of every documented CLI mode, added because
#           upstream has none.  The ;ENTROPY= values asserted here are exact:
#           they are pure functions of the argument (n*log2(8192)=13.00/word
#           for Diceware, n*log2(2048)=11.00/word for S/Key, 5.17/component
#           for the alphanumeric and special classes, 7.75 for syllables,
#           bytes<<3 for -r and bytes*7 for -k), so they also pin down the
#           entropy accounting on this platform's libm.
#   H1-H3   HarmonyOS-specific runtime behaviour:
#           H1 E051 — an unprivileged process that issues the privileged-id
#              syscall is killed by an *uncatchable* SIGSYS (exit 159) on
#              HarmonyOS.  patches/0001 makes drop_privileges() skip the
#              no-op seteuid(getuid()); this case proves the packaged binary
#              survives startup and never reports "FATAL: system call failed".
#           H2 secure-memory degradation — mlockall(MCL_FUTURE)/mlock() and
#              setrlimit(RLIMIT_CORE) may be refused inside the OHOS
#              application sandbox; upstream treats that as non-fatal and
#              prints "WARNING: using insecure memory.".  This case requires
#              a correct passphrase either way, and records which path ran.
#           H3 entropy source — RAND_bytes must be seeded from the OHOS
#              kernel RNG: two invocations must not repeat.
set -u

BINDIR="${1:-}"

# ---------------------------------------------------------------- TMPDIR
if [ -n "${TMPDIR:-}" ] && [ -d "$TMPDIR" ]; then
    :
elif [ -n "${TMP:-}" ] && [ -d "$TMP" ]; then
    TMPDIR="$TMP"
elif [ -n "${TEMP:-}" ] && [ -d "$TEMP" ]; then
    TMPDIR="$TEMP"
elif [ -n "${HOME:-}" ] && [ -d "$HOME" ]; then
    TMPDIR="$HOME/tmp"
else
    TMPDIR="$PWD/tmp"
fi
mkdir -p "$TMPDIR" 2>/dev/null || true
export TMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

TOTAL=13
PASS_COUNT=0
FAIL_COUNT=0

emit_markers() {
    # Upstream audit marker (authority: test_package/MANIFEST.yml).
    echo 'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none","command":"audit: no upstream test framework","reason":"secpwgen 1.3 ships no upstream test framework: Makefile.proto declares only all/install-strip/install/clean (no check or test target), there is no test/tests directory and no gtest/pytest/criterion bindings.","discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0}'
    if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
        echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"/bin/sh test.sh","discovered":13,"passedCount":13}'
    else
        echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"/bin/sh test.sh","discovered":13,"passedCount":'"$PASS_COUNT"'}'
    fi
}

ok() {
    echo "ok: $1"
    PASS_COUNT=$((PASS_COUNT+1))
}

nok() {
    echo "FAIL: $1"
    FAIL_COUNT=$((FAIL_COUNT+1))
}

abort() {
    echo "[test] ABORT: $1"
    PASS_COUNT=0
    FAIL_COUNT=$TOTAL
    emit_markers
    exit 1
}

echo "[test] secpwgen 1.3 HarmonyOS consumer suite (bindir='${BINDIR:-}')"

if [ -z "$BINDIR" ] || [ ! -d "$BINDIR" ]; then
    abort "bindir not resolved"
fi
if [ ! -x "$BINDIR/secpwgen" ]; then
    ls -la "$BINDIR" 2>&1 || true
    abort "$BINDIR/secpwgen missing or not executable"
fi
echo "[test] bindir listing:"
ls -la "$BINDIR" 2>&1 || true

SEC="$BINDIR/secpwgen"

# ------------------------------------------------------------------- F1
# Diceware passphrase: 4 words, 4*log2(8192) = 52.00 bits.
echo "[test] case F1: diceware_passphrase_4_words"
"$SEC" -p 4 </dev/null >"$TMPDIR/f1.out" 2>"$TMPDIR/f1.err"
F1_RC=$?
if [ "$F1_RC" -eq 0 ] \
&& grep -qE '^[^ ]+ [^ ]+ [^ ]+ [^ ]+  ;ENTROPY=52\.00 bits$' "$TMPDIR/f1.out" \
&& grep -q '^----------------$' "$TMPDIR/f1.out"; then
    ok "F1 diceware_passphrase_4_words (rc=0, 4 words, ENTROPY=52.00)"
else
    echo "  rc=$F1_RC (expected 0 + 4-word line with ENTROPY=52.00)"
    cat "$TMPDIR/f1.out" "$TMPDIR/f1.err" 2>/dev/null || true
    nok "F1 diceware_passphrase_4_words"
fi

# ------------------------------------------------------------------- F2
# Enhanced Diceware: 5 words, entropy strictly above the plain 5*13=65.00
# because each word also carries an injected symbol and its position.
echo "[test] case F2: diceware_enhanced_5_words"
"$SEC" -pe 5 </dev/null >"$TMPDIR/f2.out" 2>"$TMPDIR/f2.err"
F2_RC=$?
if [ "$F2_RC" -eq 0 ] \
&& grep -qE '^[^ ]+ [^ ]+ [^ ]+ [^ ]+ [^ ]+  ;ENTROPY=[0-9]+\.[0-9][0-9] bits$' "$TMPDIR/f2.out" \
&& ! grep -q ';ENTROPY=65\.00 bits' "$TMPDIR/f2.out"; then
    ok "F2 diceware_enhanced_5_words (rc=0, 5 words, entropy enhanced above 65.00)"
else
    echo "  rc=$F2_RC"
    cat "$TMPDIR/f2.out" "$TMPDIR/f2.err" 2>/dev/null || true
    nok "F2 diceware_enhanced_5_words"
fi

# ------------------------------------------------------------------- F3
# S/Key passphrase: 4 words from the 2048-word list, 4*log2(2048) = 44.00.
echo "[test] case F3: skey_passphrase_4_words"
"$SEC" -s 4 </dev/null >"$TMPDIR/f3.out" 2>"$TMPDIR/f3.err"
F3_RC=$?
if [ "$F3_RC" -eq 0 ] \
&& grep -qE '^[a-z]+ [a-z]+ [a-z]+ [a-z]+  ;ENTROPY=44\.00 bits$' "$TMPDIR/f3.out"; then
    ok "F3 skey_passphrase_4_words (rc=0, 4 words, ENTROPY=44.00)"
else
    echo "  rc=$F3_RC"
    cat "$TMPDIR/f3.out" "$TMPDIR/f3.err" 2>/dev/null || true
    nok "F3 skey_passphrase_4_words"
fi

# ------------------------------------------------------------------- F4
# Enhanced S/Key: entropy must exceed the plain 4*11=44.00.
echo "[test] case F4: skey_enhanced_4_words"
"$SEC" -se 4 </dev/null >"$TMPDIR/f4.out" 2>"$TMPDIR/f4.err"
F4_RC=$?
if [ "$F4_RC" -eq 0 ] \
&& grep -qE '^[^ ]+ [^ ]+ [^ ]+ [^ ]+  ;ENTROPY=[0-9]+\.[0-9][0-9] bits$' "$TMPDIR/f4.out" \
&& ! grep -q ';ENTROPY=44\.00 bits' "$TMPDIR/f4.out"; then
    ok "F4 skey_enhanced_4_words (rc=0, 4 words, entropy enhanced above 44.00)"
else
    echo "  rc=$F4_RC"
    cat "$TMPDIR/f4.out" "$TMPDIR/f4.err" 2>/dev/null || true
    nok "F4 skey_enhanced_4_words"
fi

# ------------------------------------------------------------------- F5
# ASCII random, alphanumeric class only: exactly 16 chars of [A-Z0-9] and
# 16*5.17 = 82.72 bits.
echo "[test] case F5: ascii_alphanumeric_16"
"$SEC" -Aa 16 </dev/null >"$TMPDIR/f5.out" 2>"$TMPDIR/f5.err"
F5_RC=$?
if [ "$F5_RC" -eq 0 ] \
&& grep -qE '^[A-Z0-9]{16} ;ENTROPY=82\.72 bits$' "$TMPDIR/f5.out"; then
    ok "F5 ascii_alphanumeric_16 (rc=0, 16 chars [A-Z0-9], ENTROPY=82.72)"
else
    echo "  rc=$F5_RC"
    cat "$TMPDIR/f5.out" "$TMPDIR/f5.err" 2>/dev/null || true
    nok "F5 ascii_alphanumeric_16"
fi

# ------------------------------------------------------------------- F6
# Mixed classes: get_allowed_characters("adhs") collapses to
# alphanumeric|special (both 5.17 bits), so entropy is 20*5.17 = 103.40.
# The special table holds four two-character tokens ("--" "==" ".." "//"),
# so the field is at least 20 characters, not exactly 20.
echo "[test] case F6: ascii_mixed_classes_20"
"$SEC" -Aadhs 20 </dev/null >"$TMPDIR/f6.out" 2>"$TMPDIR/f6.err"
F6_RC=$?
if [ "$F6_RC" -eq 0 ] \
&& grep -qE '^.{20,} ;ENTROPY=103\.40 bits$' "$TMPDIR/f6.out"; then
    ok "F6 ascii_mixed_classes_20 (rc=0, >=20 chars, ENTROPY=103.40)"
else
    echo "  rc=$F6_RC"
    cat "$TMPDIR/f6.out" "$TMPDIR/f6.err" 2>/dev/null || true
    nok "F6 ascii_mixed_classes_20"
fi

# ------------------------------------------------------------------- F7
# Raw random: 128 bits = 16 bytes = 22 base64 chars + "==" padding,
# entropy reported as bytes<<3 = 128.00.
echo "[test] case F7: raw_base64_128_bits"
"$SEC" -r 128 </dev/null >"$TMPDIR/f7.out" 2>"$TMPDIR/f7.err"
F7_RC=$?
if [ "$F7_RC" -eq 0 ] \
&& grep -qE '^[A-Za-z0-9+/]{22}== ;ENTROPY=128\.00 bits$' "$TMPDIR/f7.out"; then
    ok "F7 raw_base64_128_bits (rc=0, 24-char base64, ENTROPY=128.00)"
else
    echo "  rc=$F7_RC"
    cat "$TMPDIR/f7.out" "$TMPDIR/f7.err" 2>/dev/null || true
    nok "F7 raw_base64_128_bits"
fi

# ------------------------------------------------------------------- F8
# koremutake (new in 1.3): 128 bits round up to 19 syllables, entropy
# reported as bytes*7 = 133.00, output is uppercase syllables only.
echo "[test] case F8: koremutake_128_bits"
"$SEC" -k 128 </dev/null >"$TMPDIR/f8.out" 2>"$TMPDIR/f8.err"
F8_RC=$?
if [ "$F8_RC" -eq 0 ] \
&& grep -qE '^[A-Z]+ ;ENTROPY=133\.00 bits$' "$TMPDIR/f8.out"; then
    ok "F8 koremutake_128_bits (rc=0, uppercase syllables, ENTROPY=133.00)"
else
    echo "  rc=$F8_RC"
    cat "$TMPDIR/f8.out" "$TMPDIR/f8.err" 2>/dev/null || true
    nok "F8 koremutake_128_bits"
fi

# ------------------------------------------------------------------- F9
# argc != 3 → usage() on stderr → exit 1.
echo "[test] case F9: usage_no_arguments"
"$SEC" </dev/null >"$TMPDIR/f9.out" 2>"$TMPDIR/f9.err"
F9_RC=$?
if [ "$F9_RC" -eq 1 ] \
&& grep -q 'USAGE:' "$TMPDIR/f9.err" \
&& grep -q 'RAW RANDOM' "$TMPDIR/f9.err"; then
    ok "F9 usage_no_arguments (rc=1, usage on stderr)"
else
    echo "  rc=$F9_RC (expected 1)"
    cat "$TMPDIR/f9.err" 2>/dev/null || true
    nok "F9 usage_no_arguments"
fi

# ------------------------------------------------------------------ F10
# N < 1 → explicit error before usage() → exit 1.
echo "[test] case F10: reject_zero_length"
"$SEC" -p 0 </dev/null >"$TMPDIR/f10.out" 2>"$TMPDIR/f10.err"
F10_RC=$?
if [ "$F10_RC" -eq 1 ] \
&& grep -q 'ERROR: N must be an integer > 0' "$TMPDIR/f10.err"; then
    ok "F10 reject_zero_length (rc=1, N>0 validation)"
else
    echo "  rc=$F10_RC (expected 1)"
    cat "$TMPDIR/f10.err" 2>/dev/null || true
    nok "F10 reject_zero_length"
fi

# ------------------------------------------------------------------- H1
# HarmonyOS E051: the unpatched binary calls seteuid(getuid()) during
# secure_memory_init(); on HarmonyOS an unprivileged process issuing the
# privileged-id syscall is terminated by an uncatchable SIGSYS (exit code
# 159) and never reaches the generator.  Require: not killed by SIGSYS and
# no fatal system-call diagnostic.
echo "[test] case H1: harmonyos_e051_no_sigsys_on_privilege_drop"
if [ "$F1_RC" -ne 159 ] \
&& ! grep -q 'FATAL: system call failed' "$TMPDIR/f1.err" \
&& ! grep -q 'FATAL' "$TMPDIR/f1.err"; then
    ok "H1 harmonyos_e051_no_sigsys_on_privilege_drop (rc=$F1_RC != 159, no FATAL on stderr)"
else
    echo "  rc=$F1_RC; SIGSYS(159) or a FATAL system-call diagnostic means the"
    echo "  drop_privileges() guard is missing/ineffective (knowledge E051)."
    cat "$TMPDIR/f1.err" 2>/dev/null || true
    nok "H1 harmonyos_e051_no_sigsys_on_privilege_drop"
fi

# ------------------------------------------------------------------- H2
# HarmonyOS sandbox: mlockall(MCL_FUTURE)/mlock() and setrlimit(RLIMIT_CORE)
# may be refused.  Upstream degrades to "WARNING: using insecure memory."
# and keeps working; require a correct passphrase on either path.
echo "[test] case H2: harmonyos_secure_memory_degradation"
"$SEC" -Aa 12 </dev/null >"$TMPDIR/h2.out" 2>"$TMPDIR/h2.err"
H2_RC=$?
if grep -q 'WARNING: using insecure memory' "$TMPDIR/h2.err"; then
    echo "  [info] locked memory was refused by the platform (insecure-memory path)"
else
    echo "  [info] locked memory was granted (mlockall/mlock path)"
fi
if [ "$H2_RC" -eq 0 ] \
&& grep -qE '^[A-Z0-9]{12} ;ENTROPY=62\.04 bits$' "$TMPDIR/h2.out" \
&& ! grep -q 'FATAL' "$TMPDIR/h2.err"; then
    ok "H2 harmonyos_secure_memory_degradation (rc=0, valid passphrase, no FATAL)"
else
    echo "  rc=$H2_RC"
    cat "$TMPDIR/h2.out" "$TMPDIR/h2.err" 2>/dev/null || true
    nok "H2 harmonyos_secure_memory_degradation"
fi

# ------------------------------------------------------------------- H3
# HarmonyOS entropy source: RAND_bytes seeds the Blowfish-based SRNG, so two
# invocations must differ.  Identical output would mean the OHOS kernel RNG
# is not reachable and every generated secret is predictable.
echo "[test] case H3: harmonyos_entropy_source_not_repeating"
"$SEC" -r 128 </dev/null >"$TMPDIR/h3a.out" 2>"$TMPDIR/h3a.err"
H3A_RC=$?
"$SEC" -r 128 </dev/null >"$TMPDIR/h3b.out" 2>"$TMPDIR/h3b.err"
H3B_RC=$?
if [ "$H3A_RC" -eq 0 ] && [ "$H3B_RC" -eq 0 ] \
&& ! cmp -s "$TMPDIR/h3a.out" "$TMPDIR/h3b.out"; then
    ok "H3 harmonyos_entropy_source_not_repeating (two -r 128 runs differ)"
else
    echo "  rc=$H3A_RC/$H3B_RC; identical output means the CSPRNG is not seeded"
    cat "$TMPDIR/h3a.out" "$TMPDIR/h3b.out" 2>/dev/null || true
    nok "H3 harmonyos_entropy_source_not_repeating"
fi

# ---------------------------------------------------------------- summary
emit_markers
echo "[test] summary: pass=$PASS_COUNT fail=$FAIL_COUNT (of $TOTAL)"

if [ "$FAIL_COUNT" -eq 0 ] && [ "$PASS_COUNT" -eq "$TOTAL" ]; then
    exit 0
fi
exit 1
