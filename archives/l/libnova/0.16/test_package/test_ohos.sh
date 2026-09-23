#!/usr/bin/env bash
# OHOS-specific package checks for libnova/0.16 (fail-closed, 1/1 test).
#
# Usage:
#   test_ohos.sh <package_folder> <exe> <readelf> <llvm-objcopy> <binary-sign-tool>
#
# Checkpoints (all must pass; nothing is silently skipped):
#   C1  required tools resolvable (readelf / llvm-objcopy /
#       binary-sign-tool, plus ar when the package is static)
#   C2  packaged library present in <pkg>/lib (shared or static; the mode
#       is detected and logged - both modes are exercised by CI)
#   C3  static: every ar archive member is an ELF64 / Little-Endian /
#       AArch64 REL object (an archive has no SONAME by definition)
#   C4  shared: the library is ELF64 / Little-Endian / AArch64 (DYN)
#   C5  shared: DT_SONAME is exactly libnova-0.16.so.0 and the matching
#       soname file exists in lib/ (libtool -release 0.16 -version-info 0)
#   C6  DT_NEEDED of the library (shared) and of the test executable are
#       within the OHOS musl allowlist (libc.so, libm.so,
#       libnova-0.16.so.0); no GLIBC_* versioned symbols anywhere
#   C7  no RPATH / RUNPATH in the shared library or the test executable
#   C8  no build-machine absolute paths embedded in the library, the
#       public headers or the test executable
#   C9  the test executable is ELF64 / Little-Endian / AArch64 with a
#       musl PT_INTERP (aarch64 ld-musl dynamic loader)
#   C10 the test executable carries an OpenHarmony .codesign section
#       (self-signed via llvm-objcopy + binary-sign-tool, same flow as
#       the boost/1.91.0 consumer recipe)
#   C11 the executable runs on this OpenHarmony PC and its three
#       textbook-anchored astronomy assertions pass
set -euo pipefail

PKG=$1
EXE=$2
READELF=$3
OBJCOPY=$4
SIGNTOOL=$5

section() { printf '[ohos-check] %s\n' "$1"; }
die() { printf '[ohos-check] FAIL: %s\n' "$1" >&2; exit 1; }
ok() { printf '[ohos-check]   ok: %s\n' "$1"; }

section "C1: tool availability"
for t in "$READELF" "$OBJCOPY" "$SIGNTOOL"; do
    [ -x "$t" ] || die "required tool not executable: $t"
done
[ -x "$EXE" ] || die "test executable not executable: $EXE"
AR_BIN=$(command -v ar || true)

section "C2: packaged library"
LIBDIR=$PKG/lib
[ -d "$LIBDIR" ] || die "no lib/ dir in package: $LIBDIR"
shopt -s nullglob
SHLIBS=("$LIBDIR"/libnova-0.16.so.0*)
if [ "${#SHLIBS[@]}" -gt 0 ]; then
    MODE=shared
    LIB=${SHLIBS[0]}
elif [ -f "$LIBDIR/libnova.a" ]; then
    MODE=static
    LIB=$LIBDIR/libnova.a
else
    die "no libnova library found in $LIBDIR (neither libnova-0.16.so.0* nor libnova.a)"
fi
ok "mode=$MODE library=$LIB"

TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT

elf_arch_check() {  # elf_arch_check <file> <expected-type>
    local hdr
    hdr=$("$READELF" -h "$1")
    echo "$hdr" | grep -q 'Class:.*ELF64' || die "$1: not ELF64"
    echo "$hdr" | grep -q 'Data:.*little endian' \
        || die "$1: not little-endian"
    echo "$hdr" | grep -q 'Machine:.*AArch64' || die "$1: not AArch64"
    echo "$hdr" | grep -q "Type:.*$2" || die "$1: ELF type is not $2"
}

needed_allowlist_check() {  # needed_allowlist_check <file>
    local n
    while IFS= read -r n; do
        case "$n" in
            libc.so|libm.so|libnova-0.16.so.0) ;;
            *) die "$1: DT_NEEDED entry '$n' outside the OHOS musl allowlist (libc.so, libm.so, libnova-0.16.so.0)" ;;
        esac
    done < <("$READELF" -d "$1" | grep NEEDED | sed 's/.*\[\(.*\)\]$/\1/')
    ok "$1: DT_NEEDED within musl allowlist"
}

no_glibc_check() {  # no_glibc_check <file>
    if "$READELF" --version-info "$1" 2>/dev/null | grep -q 'GLIBC_'; then
        die "$1: glibc versioned symbols (GLIBC_*) found"
    fi
    ok "$1: no GLIBC_* versioned symbols"
}

no_rpath_check() {  # no_rpath_check <file>
    if "$READELF" -d "$1" | grep -qE '(RPATH|RUNPATH)'; then
        die "$1: RPATH/RUNPATH entry found"
    fi
    ok "$1: no RPATH/RUNPATH"
}

if [ "$MODE" = static ]; then
    section "C3: static archive members (ELF64 / LE / AArch64 REL)"
    [ -n "$AR_BIN" ] || die "static package check requires ar on PATH"
    ( cd "$TMPD" && "$AR_BIN" x "$LIB" )
    shopt -s nullglob
    OBJS=("$TMPD"/*.o)
    [ "${#OBJS[@]}" -gt 0 ] || die "archive contains no object members"
    for o in "${OBJS[@]}"; do
        elf_arch_check "$o" REL
    done
    ok "${#OBJS[@]} archive members are ELF64 / little-endian / AArch64 REL"
    section "C4/C5: n/a for a static archive (no SONAME claim - logged, not skipped silently)"
else
    section "C3: n/a for a shared package (logged, not skipped silently)"
    section "C4: shared library ELF identity"
    elf_arch_check "$LIB" DYN
    ok "library is ELF64 / little-endian / AArch64 DYN"

    section "C5: SONAME"
    SONAME=$("$READELF" -d "$LIB" | sed -n 's/.*SONAME.*\[\(.*\)\]$/\1/p')
    [ -n "$SONAME" ] || die "library has no DT_SONAME"
    [ "$SONAME" = "libnova-0.16.so.0" ] \
        || die "DT_SONAME is '$SONAME', expected libnova-0.16.so.0"
    [ -e "$LIBDIR/$SONAME" ] \
        || die "soname file $LIBDIR/$SONAME does not exist"
    ok "DT_SONAME=$SONAME matches the installed filename"
fi

section "C6: DT_NEEDED allowlist + no glibc linkage"
if [ "$MODE" = shared ]; then
    needed_allowlist_check "$LIB"
    no_glibc_check "$LIB"
else
    ok "static archive: no dynamic section in the library itself (exe checked below)"
fi
needed_allowlist_check "$EXE"
no_glibc_check "$EXE"

section "C7: no RPATH / RUNPATH"
if [ "$MODE" = shared ]; then
    no_rpath_check "$LIB"
fi
no_rpath_check "$EXE"

section "C8: no build-machine absolute paths embedded"
LEAK_RE='(/home/|/storage/Users/|\.conan2/p/)'
if grep -a -q -E "$LEAK_RE" "$LIB"; then
    die "build-machine absolute path embedded in $LIB"
fi
if grep -a -r -q -E "$LEAK_RE" "$PKG/include"; then
    die "build-machine absolute path embedded in $PKG/include"
fi
if grep -a -q -E "$LEAK_RE" "$EXE"; then
    die "build-machine absolute path embedded in $EXE"
fi
ok "no build-machine absolute paths in library / headers / executable"

section "C9: test executable ELF identity + musl PT_INTERP"
elf_arch_check "$EXE" DYN
if ! "$READELF" -l "$EXE" | grep -A2 INTERP | grep -q musl; then
    die "$EXE: no musl PT_INTERP (aarch64 ld-musl loader) found"
fi
ok "executable is ELF64 / little-endian / AArch64 with musl PT_INTERP"

section "C10: OpenHarmony .codesign section"
SIGNED=$TMPD/ohos_check.signed
cp "$EXE" "$SIGNED"
"$OBJCOPY" --remove-section .codesign "$SIGNED" 2>/dev/null || true
"$SIGNTOOL" sign -inFile "$SIGNED" -outFile "$SIGNED" -selfSign 1 \
    || die "binary-sign-tool failed to self-sign the executable"
chmod +x "$SIGNED"
if ! "$READELF" -S "$SIGNED" | grep -q '\.codesign'; then
    die "no .codesign section present after self-signing"
fi
ok ".codesign section present after self-signing"

section "C11: real astronomy run on the OpenHarmony PC"
OUT=$TMPD/ohos_check.out
if ! "$SIGNED" > "$OUT" 2>&1; then
    cat "$OUT" >&2
    die "signed astronomy check executable failed on this device"
fi
cat "$OUT"
grep -q 'OHOS_ASTRONOMY_OK' "$OUT" \
    || die "astronomy check did not report OHOS_ASTRONOMY_OK"

section "ALL 11 CHECKPOINTS PASSED"
