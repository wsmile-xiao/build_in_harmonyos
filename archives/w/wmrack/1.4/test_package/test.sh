#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for wmrack 1.4
#
# Runs inside the conanrun environment: PATH already contains the installed
# bin/ and LD_LIBRARY_PATH contains the libX11 / libXpm / libXext packages the
# binary links against.  OHOS has no X server, so the GUI itself cannot be
# driven; the tests below cover the strongest consumer-visible behaviour that is
# reachable and they all exercise the *installed package*, not a rebuild:
#   1. the binary is installed on PATH
#   2. the packaged artifact is an AArch64 ELF64 executable
#   3. the dynamic dependency chain is recorded in the artifact
#   4. the XPM style selected at build time is compiled into the binary
#   5. the CLI contract (`wmrack --help` -> upstream usage(), exit status 1)
#   6. running the binary executes main() up to its device/display stage
#      (proves the whole X11/Xpm/Xext shared-library chain loads and relocates)
#   7. the installed data files (style library + man page) are present
#
# The binary artifacts are inspected as raw bytes (od) and matched with bash
# pattern matching instead of `grep -a`: on OHOS `grep` may resolve to toybox,
# whose binary-file handling silently reports "no match".
set -euo pipefail

export LC_ALL=C
# lib_findfile() does strcpy(path, getenv("HOME")) — HOME must never be empty.
export HOME="${HOME:-$PWD}"
# Make the "no X server" branch deterministic.
unset DISPLAY 2> /dev/null || true

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

# hex_of STRING — raw hex dump of a literal string (bash builtin + od only).
hex_of() {
    printf '%s' "$1" | od -An -tx1 | tr -d ' \n'
}

# assert_bytes BLOB LITERAL WHAT — plain-string search inside a hex blob.
assert_bytes() {
    local needle
    needle="$(hex_of "$2")"
    case "$1" in
        *"$needle"*) echo "OK: $3 -> \"$2\"" ;;
        *) fail "$3 missing: \"$2\" not present in the packaged artifact" ;;
    esac
}

echo "[test 1] wmrack is installed on PATH"
command -v wmrack > /dev/null || fail "wmrack not found on PATH"
WM="$(command -v wmrack)"
PKG_ROOT="$(cd "$(dirname "$WM")/.." && pwd)"
echo "OK: $WM"

echo "[test 2] packaged artifact is an AArch64 ELF64 executable"
SIZE="$(wc -c < "$WM" | tr -d ' ')"
[ "$SIZE" -gt 0 ] || fail "the installed wmrack is empty"
MAGIC="$(od -An -tx1 -N4 "$WM" | tr -d ' \n')"
[ "$MAGIC" = "7f454c46" ] || fail "not an ELF file (magic=$MAGIC)"
CLASS="$(od -An -tx1 -j4 -N1 "$WM" | tr -d ' \n')"
[ "$CLASS" = "02" ] || fail "not ELF64 (ei_class=$CLASS)"
MACHINE="$(od -An -tx1 -j18 -N2 "$WM" | tr -d ' \n')"
[ "$MACHINE" = "b700" ] || fail "not AArch64 little-endian (e_machine=$MACHINE)"
echo "OK: $SIZE bytes, ELF64 / EM_AARCH64 / little-endian"

echo "[test 3] dynamic dependency chain is recorded in the artifact"
BLOB="$(od -An -v -tx1 "$WM" | tr -d ' \n')"
[ "${#BLOB}" -eq $((SIZE * 2)) ] \
    || fail "raw byte dump truncated (${#BLOB} hex chars for $SIZE bytes)"
for lib in libX11.so.6 libXpm.so.4 libXext.so.6; do
    assert_bytes "$BLOB" "$lib" "DT_NEEDED entry"
done
assert_bytes "$BLOB" "XOpenDisplay" "X11 entry point"

echo "[test 4] the XPM style selected at build time is compiled into the binary"
# xpmicon.c does `#include "XPM/standart.style"`; standart.style is the symbolic
# link to grey.style created by the Makefile.  "296 11 4 1" is the alphaled
# geometry of the grey style only (clean.style uses "296 11 2 1"), so finding it
# proves the symlinked style was really compiled in.
assert_bytes "$BLOB" "296 11 4 1" "compiled-in default (grey) style"

echo "[test 5] wmrack --help reproduces the upstream CLI contract"
set +e
HELP_OUTPUT="$("$WM" --help 2>&1)"
HELP_STATUS=$?
set -e
case "$HELP_OUTPUT" in
    *"wmrack - Version 1.4"*) echo "OK: version banner" ;;
    *) fail "--help did not print the version banner: $HELP_OUTPUT" ;;
esac
case "$HELP_OUTPUT" in
    *"usage: wmrack [OPTIONS]"*) echo "OK: usage line" ;;
    *) fail "--help did not print the usage line" ;;
esac
[ "$HELP_STATUS" -eq 1 ] || fail "upstream usage() exits 1, got $HELP_STATUS"
echo "OK: --help banner + usage, exit status 1"

echo "[test 6] running wmrack executes main() (X11/Xpm/Xext load chain resolves)"
set +e
RUN_OUTPUT="$("$WM" 2>&1)"
set -e
# wmrack's main() opens the OSS mixer before contacting the X server, so the
# exact stopping point is environment dependent:
#   * OHOS (no /dev/mixer):         "wmrack: can't read mixer file"
#   * desktop without a display:    "can't open display"
# Both outcomes prove the same consumer property: every shared library of the
# X11/Xpm/Xext chain was found, exec-mapped and relocated, and main() ran far
# enough to probe real devices.
case "$RUN_OUTPUT" in
    *"can't read mixer file"*|*"can't open display"*) ;;
    *) fail "wmrack run did not reach its device/display stage; output was: $RUN_OUTPUT" ;;
esac
case "$RUN_OUTPUT" in
    *"can't open display"*)
        echo "OK: reached XOpenDisplay (\"can't open display\") — X11 chain resolved"
        ;;
    *)
        echo "OK: reached the mixer stage (\"can't read mixer file\") — Xpm/X11/Xext chain resolved"
        ;;
esac

echo "[test 7] installed data files (style library + man page)"
for asset in "bin/wmrack" "lib/WMRack/grey.style" "lib/WMRack/clean.style" "share/man/man1/wmrack.1"; do
    [ -s "$PKG_ROOT/$asset" ] || fail "$asset is missing or empty"
    echo "OK: $asset"
done

echo "ALL CONSUMER TESTS PASSED"
