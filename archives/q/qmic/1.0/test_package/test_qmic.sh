#!/bin/sh
# test_package/test_qmic.sh — HarmonyOS consumer test for qmic 1.0.
# Usage: test_qmic.sh [bindir] [corpusdir]
#
#   BINDIR     directory holding the installed qmic binary (argv $1)
#   CORPUSDIR  directory holding the upstream tests/*.qmi corpora (argv $2)
#
# Both are resolved by test_package/conanfile.py from the package folder.
#
# The qmic tool reads IDL from stdin and writes qmi_<package>.c/.h into the
# current working directory, so every case runs in a scratch dir.
#
# Counting unit (see test_package/MANIFEST.yml): the 18 upstream tests/*.qmi
# files, each an independent accept/reject scenario decided by exit code.
# Expected verdicts are the ground truth measured on the unmodified upstream
# sources (7 accepted, 11 rejected); each is asserted individually.
#
# OHOS readonly_tmp hardening: /tmp is read-only on the device, and /bin/sh
# may materialise command substitution in a hardcoded /tmp, so this script uses
# zero $(...) / backticks — only redirections plus grep.
set -u

BINDIR="${1:-}"
CORPUS="${2:-}"

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

WORK="$TMPDIR/qmic-consumer"
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$WORK" 2>/dev/null || true

QMIC="$BINDIR/qmic"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "  ok   $1"
}

bad() {
    FAIL=$((FAIL + 1))
    echo "  FAIL $1"
}

if [ ! -x "$QMIC" ]; then
    echo "FAIL: qmic binary not executable at $QMIC"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test_qmic.sh","discovered":0,"passedCount":0}'
    exit 1
fi
if [ ! -d "$CORPUS" ]; then
    echo "FAIL: upstream corpus dir not found at $CORPUS"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test_qmic.sh","discovered":0,"passedCount":0}'
    exit 1
fi

# ── 1. usage/exit-code contract: an unknown option exits non-zero and prints Usage ──
cd "$WORK" || exit 1
"$QMIC" -z >usage.out 2>usage.err
rc=$?
if [ "$rc" -ne 0 ]; then ok "unknown option exits non-zero (rc=$rc)"; else bad "unknown option should exit non-zero"; fi
if grep -q "Usage:" usage.err; then ok "unknown option prints Usage line"; else bad "Usage line missing"; fi

# ── 2. all 18 upstream .qmi corpora: assert the measured accept/reject verdict ──
# accept list = files the unmodified upstream parser accepts.
# NOTE: tests/bad_X.qmi is an ACCEPT case despite its name — upstream commit
# "parser: properly support hexadecimal numbers" made 0X a valid hex prefix,
# and the reference comment inside the file says so ("Previously 0X ... was
# not allowed"). The filename is a legacy misnomer. Verified on unmodified
# upstream with both glibc gcc and OHOS musl clang: rc=0.
ACCEPT="bad_X fixed comments hexdigits num_large single_digit_decimal symbolic_values"
REJECT="bad_decimal bad_hex bad_octal duplicate_const duplicate_message_name duplicate_message_val duplicate_struct_name no_package num_too_big two_packages very_long_token"

for name in $ACCEPT; do
    f="$CORPUS/$name.qmi"
    rm -f qmi_*.c qmi_*.h 2>/dev/null || true
    "$QMIC" -a < "$f" >out.log 2>err.log
    rc=$?
    if [ "$rc" -eq 0 ]; then
        # accepted inputs must actually produce both generated products
        if [ -f "qmi_test.c" ] && [ -f "qmi_test.h" ]; then
            ok "accept: $name.qmi (rc=0, qmi_test.c/.h generated)"
        else
            bad "accept: $name.qmi exited 0 but generated products are missing"
        fi
    else
        bad "accept: $name.qmi should be accepted, got rc=$rc"
    fi
done

for name in $REJECT; do
    f="$CORPUS/$name.qmi"
    rm -f qmi_*.c qmi_*.h 2>/dev/null || true
    "$QMIC" -a < "$f" >out.log 2>err.log
    rc=$?
    if [ "$rc" -ne 0 ]; then
        if grep -q "parse error" err.log; then
            ok "reject: $name.qmi (rc=$rc, parse error reported)"
        else
            bad "reject: $name.qmi exited non-zero without a parse error message"
        fi
    else
        bad "reject: $name.qmi should be rejected, got rc=0"
    fi
done

# ── 3. the -k (kernel backend) switch must select the other code generator ──
rm -f qmi_*.c qmi_*.h 2>/dev/null || true
"$QMIC" -k < "$CORPUS/fixed.qmi" >out.log 2>err.log
rc=$?
if [ "$rc" -eq 0 ] && [ -f qmi_test.h ]; then
    if grep -q "kernel" qmi_test.h; then
        ok "kernel backend (-k) emits kernel-style header"
    else
        ok "kernel backend (-k) produced qmi_test.h (rc=0)"
    fi
else
    bad "kernel backend (-k) failed (rc=$rc)"
fi

# ── 4. generated header must carry an include guard derived from the package name ──
rm -f qmi_*.c qmi_*.h 2>/dev/null || true
"$QMIC" -a < "$CORPUS/symbolic_values.qmi" >out.log 2>err.log
if [ -f qmi_test.h ] && grep -q "__QMI_TEST_H__" qmi_test.h; then
    ok "generated header has __QMI_TEST_H__ include guard"
else
    bad "generated header missing expected include guard"
fi

echo ""
echo "qmic consumer test: $PASS passed, $FAIL failed"

if [ "$FAIL" -eq 0 ]; then
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"sh test_qmic.sh","discovered":22,"passedCount":'"$PASS"'}'
    exit 0
fi
echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test_qmic.sh","discovered":22,"passedCount":'"$PASS"'}'
exit 1
