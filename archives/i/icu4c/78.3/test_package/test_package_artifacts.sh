#!/bin/sh
# HarmonyOS packaging-contract checks for icu4c 78.3 (consumer-side, package layout).
# Runs on the device against the Conan package folder, not against the build tree.
#   usage: sh test_package_artifacts.sh <package_folder>
set -u

PKG="${1:?usage: test_package_artifacts.sh <package_folder>}"
LIB="$PKG/lib"
INC="$PKG/include/unicode"
BIN="$PKG/bin"

TOTAL=0
PASS=0
FAIL=0

check() {
    desc="$1"
    shift
    TOTAL=$((TOTAL + 1))
    if "$@" >/dev/null 2>&1; then
        PASS=$((PASS + 1))
        printf '[PASS] %s\n' "$desc"
    else
        FAIL=$((FAIL + 1))
        printf '[FAIL] %s\n' "$desc"
    fi
}

at_least_bytes() {
    # at_least_bytes <file> <bytes>
    size=$(wc -c <"$1" 2>/dev/null | tr -d ' ')
    [ -n "$size" ] && [ "$size" -gt "$2" ]
}

elf_magic() {
    [ "$(dd if="$1" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "7f454c46" ]
}

elf_is_aarch64() {
    # e_machine is a 16-bit little-endian field at offset 18; 0xb7 = EM_AARCH64.
    [ "$(dd if="$1" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')" = "b700" ]
}

check "package folder exists" test -d "$PKG"
check "headers installed" test -d "$INC"
check "uvernum.h declares ICU 78.3" grep -q '"78.3"' "$INC/uvernum.h"
check "static libicudata.a present" test -f "$LIB/libicudata.a"
check "static libicuuc.a present" test -f "$LIB/libicuuc.a"
check "static libicui18n.a present" test -f "$LIB/libicui18n.a"
check "libicudata.a carries the embedded Unicode/CLDR data" at_least_bytes "$LIB/libicudata.a" 10000000
check "no shared ICU object is packaged (OHOS stubdata crash)" \
    test -z "$(find "$PKG" -name 'libicu*.so*' -o -name '*.so' 2>/dev/null)"
check "no standalone ICU data file is required by the package" \
    test -z "$(find "$PKG" -name 'icudt*.dat' 2>/dev/null)"
check "licenses/LICENSE collected" test -f "$PKG/licenses/LICENSE"
check "LICENSE is the Unicode License V3" grep -qi 'UNICODE LICENSE V3' "$PKG/licenses/LICENSE"

TOOL_COUNT=$(ls -1 "$BIN" 2>/dev/null | wc -l | tr -d ' ')
check "ICU command line tools installed in bin/" test "$TOOL_COUNT" -ge 5
check "pkgdata tool present" test -f "$BIN/pkgdata"
check "pkgdata is ELF" elf_magic "$BIN/pkgdata"
check "pkgdata is AArch64" elf_is_aarch64 "$BIN/pkgdata"
check "genrb tool present" test -f "$BIN/genrb"
check "genrb is AArch64" elf_is_aarch64 "$BIN/genrb"
check "icuinfo tool present" test -f "$BIN/icuinfo"

# Functional checks on the packaged tools. genrb names the output after the
# bundle's root item, so `root {...}` in hello.txt yields root.res.
WORK="${TMPDIR:-$HOME/tmp}/icu783-genrb.$$"
mkdir -p "$WORK" 2>/dev/null
printf 'root {\n  version { "1.0" }\n  hello { "world-icu783" }\n}\n' >"$WORK/hello.txt"
check "genrb compiles a resource bundle" sh -c "cd '$WORK' && '$BIN/genrb' hello.txt"
check "genrb wrote root.res" at_least_bytes "$WORK/root.res" 32
check "genrb -V reports the packaged ICU version" \
    sh -c "'$BIN/genrb' -V 2>&1 | grep -q 'ICU version 78.3'"
check "icuinfo runs and reports the packaged ICU version" \
    sh -c "'$BIN/icuinfo' 2>&1 | grep -q '78.3'"
rm -rf "$WORK"

printf 'TOTAL=%d PASS=%d FAIL=%d\n' "$TOTAL" "$PASS" "$FAIL"
if [ "$FAIL" -ne 0 ]; then
    printf 'SOME TESTS FAILED\n'
    exit 1
fi
printf 'ALL ARTIFACT CHECKS PASSED\n'
exit 0
