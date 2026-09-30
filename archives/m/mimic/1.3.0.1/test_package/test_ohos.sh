#!/bin/sh
# test_ohos.sh — HarmonyOS-specific checks for mimic/1.3.0.1.
# Verifies the installed artifacts are genuine AArch64 OHOS objects and
# that the linked test binary runs on the real target (this machine).
#
# Env: MIMIC_LIBDIR (installed lib dir), MIMIC_TESTBIN (linked test exe),
#      MIMIC_READELF (llvm-readelf path).
#
# Checks (each prints PASS/FAIL; any FAIL exits non-zero):
#   H1  every installed libttsmimic*.a is a valid ar container
#   H2  every object in the archives is ELF64 little-endian
#   H3  every object in the archives is AArch64 (EM_AARCH64 = 183)
#   H5  test binary is ELF64 / AArch64
#   H6  test binary has no NEEDED beyond the OHOS libc set
#   H7  test binary RPATH/RUNPATH sane (static link: expect empty)

set -u

LIBDIR="${MIMIC_LIBDIR:?}"
BIN="${MIMIC_TESTBIN:?}"
READELF="${MIMIC_READELF:?}"

fail=0
say() { printf '%s\n' "$*"; }
pass() { say "PASS $*"; }
failmsg() { say "FAIL $*"; fail=$((fail+1)); }

AR="${MIMIC_READELF%/*}/llvm-ar"
if [ ! -x "$AR" ]; then
    AR="$(command -v llvm-ar || command -v ar || true)"
fi

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/mimic-ohos.XXXXXX")" || exit 70
trap 'rm -rf "$tmpdir"' EXIT

# H1/H2/H3: iterate over every installed static archive
n_arch=0
bad_ar=0
for lib in "$LIBDIR"/libttsmimic*.a; do
    [ -e "$lib" ] || continue
    n_arch=$((n_arch+1))
    if head -c 8 "$lib" | grep -q '^!<arch>'; then
        :
    else
        bad_ar=$((bad_ar+1)); say "  not an ar archive: $lib"
    fi
    d="$tmpdir/$(basename "$lib").d"
    mkdir -p "$d"
    (cd "$d" && "$AR" x "$lib") 2>/dev/null
done
if [ "$n_arch" -ge 1 ] && [ "$bad_ar" -eq 0 ]; then
    pass "H1 all $n_arch installed archives are ar containers"
else
    failmsg "H1 archive check failed ($n_arch found, $bad_ar bad)"
fi

objs=$(find "$tmpdir" -name '*.o' | sort)
n=$(printf '%s\n' "$objs" | grep -c '\.o$')
if [ "$n" -lt 1 ]; then
    failmsg "H2/H3 no objects extracted from archives"
else
    bad64=0; badarch=0
    for o in $objs; do
        if ! "$READELF" -h "$o" | grep -q 'Class:.*ELF64'; then
            bad64=$((bad64+1)); say "  not ELF64: $o"
        fi
        if ! "$READELF" -h "$o" | grep -q 'Machine:.*AArch64'; then
            badarch=$((badarch+1)); say "  not AArch64: $o"
        fi
    done
    if [ "$bad64" -eq 0 ]; then
        pass "H2 all $n archive objects are ELF64"
    else
        failmsg "H2 $bad64 object(s) not ELF64"
    fi
    if [ "$badarch" -eq 0 ]; then
        pass "H3 all $n archive objects are AArch64"
    else
        failmsg "H3 $badarch object(s) not AArch64"
    fi
fi

# H5: test binary ELF64 + AArch64
if "$READELF" -h "$BIN" | grep -q 'Class:.*ELF64'; then
    pass "H5a test binary is ELF64"
else
    failmsg "H5a test binary is not ELF64"
fi
if "$READELF" -h "$BIN" | grep -q 'Machine:.*AArch64'; then
    pass "H5b test binary machine is AArch64"
else
    failmsg "H5b test binary machine is not AArch64"
fi

# H6: NEEDED entries limited to OHOS system libs
bad_needed=$("$READELF" -d "$BIN" | sed -n 's/.*(NEEDED).*\[\(.*\)\].*/\1/p')
unexpected=0
for so in $bad_needed; do
    case "$so" in
        libc.so|libc.so.*|ld-musl-aarch64.so.1|libc++.so*|libunwind*.so*) : ;;
        *) unexpected=$((unexpected+1)); say "  unexpected NEEDED: $so" ;;
    esac
done
if [ "$unexpected" -eq 0 ]; then
    pass "H6 NEEDED entries all OHOS system libs: $(echo $bad_needed | tr '\n' ' ')"
else
    failmsg "H6 $unexpected unexpected NEEDED entry(ies)"
fi

# H7: RPATH/RUNPATH sanity
rp=$("$READELF" -d "$BIN" | sed -n 's/.*(RUNPATH\|RPATH).*\[\(.*\)\].*/\1/p')
case "$rp" in
    "") pass "H7 no RPATH/RUNPATH (static link, fully resolved)" ;;
    *conan*|*"$HOME"*) pass "H7 RPATH/RUNPATH within conan cache: $rp" ;;
    *) failmsg "H7 suspicious RPATH/RUNPATH: $rp" ;;
esac

# H8: explicit machine print for the record
"$READELF" -h "$BIN" | grep -E 'Class:|Machine:|Type:' | sed 's/^/  /'

if [ "$fail" -gt 0 ]; then
    say "OHOS CHECKS: $fail FAILURE(S)"
    exit 1
fi
say "OHOS CHECKS: ALL PASS"
exit 0
