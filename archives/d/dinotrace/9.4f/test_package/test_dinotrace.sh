#!/bin/sh
# test_package/test_dinotrace.sh — consumer test for dinotrace 9.4f (R34 / L0c).
# Usage: sh test_dinotrace.sh <bin_dir> [<llvm-readelf>]
# Executes the packaged binary directly; asserts version, the ELF DT_NEEDED
# Motif/X11 chain, and headless behaviour.  Never hangs (timeout => FAIL).
set -u

BIN_DIR="${1:-}"
READELF="${2:-}"
[ -n "$READELF" ] || READELF="/data/service/hnp/bin/llvm-readelf"
if [ ! -x "$READELF" ]; then
    READELF="$(command -v llvm-readelf || command -v readelf || true)"
fi

A=0
F=0
pass() { A=$((A + 1)); echo "PASS: $1"; }
fail() { A=$((A + 1)); F=$((F + 1)); echo "FAIL: $1"; }

echo "=== dinotrace 9.4f consumer test ==="
echo "bin_dir=$BIN_DIR"
echo "readelf=$READELF"

if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin dir not found: '${BIN_DIR}'"
    echo "assertions=1 failures=1"
    exit 1
fi

BIN="${BIN_DIR}/dinotrace"

# (a) bin/dinotrace exists and is executable
if [ -x "$BIN" ]; then
    pass "bin/dinotrace exists and is executable"
else
    fail "bin/dinotrace missing or not executable at ${BIN}"
fi

# (b) --version exits 0 and stdout contains 'Dinotrace 9.4f'
VER_RC=127
VER_OUT=""
if [ -x "$BIN" ]; then
    VER_OUT="$(DISPLAY= "$BIN" --version 2>&1)"
    VER_RC=$?
fi
echo "--- captured: dinotrace --version (exit=${VER_RC}) ---"
echo "$VER_OUT"
echo "--- end ---"
if [ "$VER_RC" -eq 0 ] && printf '%s\n' "$VER_OUT" | grep -q "Dinotrace 9.4f"; then
    pass "--version exits 0 and stdout contains 'Dinotrace 9.4f'"
else
    fail "--version: exit=${VER_RC}, expected 0 with 'Dinotrace 9.4f'"
fi

# (c) ELF DT_NEEDED evidence: the packaged Motif/X11 chain is linked
if [ -x "$READELF" ]; then
    DYN="$("$READELF" -d "$BIN" 2>&1)"
    echo "--- captured: ${READELF} -d ... (NEEDED/SONAME lines) ---"
    printf '%s\n' "$DYN" | grep -E "NEEDED|SONAME" || true
    echo "--- end ---"
    for lib in libXm.so.4 libXt.so.6 libX11.so.6; do
        if printf '%s\n' "$DYN" | grep -q "NEEDED.*${lib}"; then
            pass "ELF DT_NEEDED ${lib}"
        else
            fail "ELF DT_NEEDED ${lib} missing"
        fi
    done
else
    fail "no usable llvm-readelf/readelf found (got '${READELF}')"
fi

# (d) headless init: DISPLAY unset, must not hang (timeout => FAIL) and must
#     emit the real upstream display error (or a genuine Xt error / version).
HL_RC=0
HL_OUT=""
if [ -x "$BIN" ]; then
    HL_OUT="$(unset DISPLAY; timeout 30 "$BIN" 2>&1)"
    HL_RC=$?
fi
echo "--- captured: headless dinotrace (DISPLAY unset, timeout 30) exit=${HL_RC} ---"
echo "$HL_OUT"
echo "--- end ---"
if [ "$HL_RC" -eq 124 ]; then
    fail "headless dinotrace hung (timeout 30 exceeded)"
elif printf '%s\n' "$HL_OUT" | grep -q "Can't open display"; then
    pass "headless dinotrace printed upstream display error and exited (${HL_RC})"
elif [ "$HL_RC" -ne 0 ] && printf '%s\n' "$HL_OUT" | grep -qiE "display|Xt[ _]?(Error|Warning)|cannot open"; then
    pass "headless dinotrace: non-zero exit (${HL_RC}) with Xt/display error"
elif [ "$HL_RC" -eq 0 ] && printf '%s\n' "$HL_OUT" | grep -q "Dinotrace 9.4f"; then
    pass "headless dinotrace exited 0 after printing version"
else
    fail "headless dinotrace: unexpected exit=${HL_RC} output='${HL_OUT}'"
fi

echo "assertions=${A} failures=${F}"
[ "$F" -eq 0 ] || exit 1
exit 0
