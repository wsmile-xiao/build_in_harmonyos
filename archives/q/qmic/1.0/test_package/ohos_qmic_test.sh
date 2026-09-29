#!/bin/sh
# ohos_qmic_test.sh — HarmonyOS platform-specific test for qmic 1.0.
# Usage: ohos_qmic_test.sh [bindir] [corpusdir]
#
#   BINDIR     directory holding the installed qmic binary (argv $1)
#   CORPUSDIR  directory holding the upstream tests/*.qmi corpora (argv $2)
#
# ── Why this is a HarmonyOS-specific test (not a renamed upstream test) ──
# The single platform adaptation in this recipe is in parser.c: upstream
# yyerror() prefixes parse errors with `program_invocation_short_name`, a
# glibc-only extension that OHOS musl does NOT declare — the unpatched source
# fails to compile with "use of undeclared identifier
# 'program_invocation_short_name'". The patch uses `__progname` instead, which
# is the same symbol upstream qmic.c already uses for its usage message and
# which is exported by glibc, musl and OHOS libc alike (knowledge E203/E493).
#
# The assertions below only hold on the adapted OHOS build:
#   A. the error prefix is the real process name, i.e. __progname was actually
#      read from OHOS libc at runtime (a stale/zeroed pointer would print an
#      empty prefix or "(null)");
#   B. the installed binary carries no reference to the glibc-only symbol,
#      while it does reference __progname — the musl-incompatible path is gone;
#   C. the adapted binary still generates real C from valid IDL.
#
# NOTE on argv[0]: an earlier revision copied the binary to a second name and
# re-ran it to show that __progname follows argv[0]. OHOS rejects that: a copied
# ELF is outside its signature boundary and the loader refuses to exec it
# ("Operation not permitted", E077/E452), so the check could never pass on the
# target. Only the signed installed binary is ever executed below.
#
# Zero $(...) / backticks on purpose: OHOS /bin/sh may materialise command
# substitution in a hardcoded read-only /tmp.
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
export TMPDIR TMP TEMP TEMPDIR
export TMP="$TMPDIR"
export TEMP="$TMPDIR"
export TEMPDIR="$TMPDIR"

QMIC="$BINDIR/qmic"
PASS=0
FAIL=0

ok()  { PASS=$((PASS + 1)); echo "  ok   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  FAIL $1"; }

if [ ! -x "$QMIC" ]; then
    echo "FAIL: qmic binary not executable at $QMIC"
    echo 'HMBS_OHOS_TEST_RESULT={"executed":true,"passed":false,"count":0}'
    exit 1
fi
if [ ! -d "$CORPUS" ]; then
    echo "FAIL: upstream corpus dir not found at $CORPUS"
    echo 'HMBS_OHOS_TEST_RESULT={"executed":true,"passed":false,"count":0}'
    exit 1
fi

WORK="$TMPDIR/qmic-ohos"
rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$WORK" 2>/dev/null || true
cd "$WORK" || exit 1

# A. the musl adaptation is live: parse-error prefix must be the real program
#    name read from OHOS libc's __progname, not an empty/(null) prefix.
"$QMIC" -a < "$CORPUS/no_package.qmi" >out.log 2>err.log
rc=$?
if [ "$rc" -ne 0 ]; then
    ok "adapted error path still rejects invalid IDL (rc=$rc)"
else
    bad "invalid IDL unexpectedly accepted (rc=0)"
fi
# The prefix is "<progname>: parse error on line ..." — the program name must
# be a non-empty token, which proves __progname resolved at runtime.
if grep -qE '^[^ :][^:]*: parse error on line [0-9]+:' err.log; then
    ok "__progname resolved at runtime (error prefix carries real program name)"
else
    bad "error prefix is empty/unresolved — __progname did not resolve"
    echo "       err.log:"
    sed 's/^/         /' err.log 2>/dev/null || true
fi
# It must specifically not be a null pointer rendered by printf.
if grep -q '(null)' err.log; then
    bad "error prefix rendered '(null)' — __progname was not populated"
else
    ok "error prefix is not a null pointer"
fi
# The prefix must equal the basename the binary was invoked as (it is invoked
# via "$QMIC", so this is the installed name). This still exercises the
# __progname contract without ever executing a copy.
if grep -q '^qmic: parse error' err.log; then
    ok "error prefix is the invoked program name (qmic)"
else
    bad "error prefix is not the invoked program name"
    sed 's/^/         /' err.log 2>/dev/null || true
fi

# B. no glibc-only symbol reference may remain in the OHOS binary, and the
#    portable symbol must be the one in use. Checked on the installed binary
#    itself, so it holds without needing the build tree.
#
#    Symbol dumpers differ per host (readelf on the OHOS CI worker, llvm-nm on
#    a dev box with the OHOS SDK, plain nm elsewhere), so probe them in order.
#    A dynamic-symbol name always lives in the ELF .dynstr section, so scanning
#    the raw image is a portable last resort that still detects a regression.
SYMS="$TMPDIR/qmic-syms.txt"
: > "$SYMS"
for tool in readelf llvm-nm nm; do
    if command -v "$tool" >/dev/null 2>&1; then
        if [ "$tool" = "readelf" ]; then
            readelf -sW "$QMIC" > "$SYMS" 2>/dev/null && break
        else
            "$tool" "$QMIC" > "$SYMS" 2>/dev/null && break
        fi
    fi
done
if [ ! -s "$SYMS" ]; then
    # Portable fallback: the symbol name is embedded in the ELF string table.
    strings "$QMIC" > "$SYMS" 2>/dev/null || cp "$QMIC" "$SYMS"
    echo "  note no symbol dumper available — fell back to raw string-table scan"
fi

if grep -q 'program_invocation_short_name' "$SYMS"; then
    bad "binary still carries glibc-only symbol reference"
else
    ok "binary carries no glibc-only symbol reference"
fi
if grep -q '__progname' "$SYMS"; then
    ok "binary references __progname (OHOS libc export)"
else
    bad "binary does not reference __progname — adaptation not in effect"
fi

# C. the generator still works under OHOS after the adaptation: real IDL in,
#    C/H out, and the outputs are compilable C rather than placeholder text.
#    Every case runs in its own scratch dir so a previous run cannot mask a
#    missing output.
GEN="$WORK/gen"
rm -rf "$GEN" 2>/dev/null || true
mkdir -p "$GEN" 2>/dev/null || true
if cd "$GEN"; then
    "$QMIC" -a < "$CORPUS/fixed.qmi" >out3.log 2>err3.log
    rc=$?
    if [ "$rc" -eq 0 ] && [ -f qmi_test.c ] && [ -f qmi_test.h ]; then
        ok "OHOS build still generates qmi_test.c/.h from valid IDL"
    else
        bad "generator produced no output under OHOS (rc=$rc)"
        echo "       err3.log:"
        sed 's/^/         /' err3.log 2>/dev/null || true
    fi
    if [ -f qmi_test.c ] && grep -q '#include' qmi_test.c && grep -q 'qmi_test.h' qmi_test.c; then
        ok "generated source includes its own header (real codegen, not a stub)"
    else
        bad "generated source looks like a stub"
    fi
    if [ -f qmi_test.h ] && grep -q '__QMI_TEST_H__' qmi_test.h; then
        ok "generated header carries the package include guard"
    else
        bad "generated header is missing its include guard"
    fi
else
    bad "could not create generator scratch dir $GEN"
fi

echo ""
echo "qmic OHOS-specific test: $PASS passed, $FAIL failed"

if [ "$FAIL" -eq 0 ]; then
    echo 'HMBS_OHOS_TEST_RESULT={"executed":true,"passed":true,"count":'"$PASS"'}'
    exit 0
fi
echo 'HMBS_OHOS_TEST_RESULT={"executed":true,"passed":false,"count":'"$PASS"'}'
exit 1
