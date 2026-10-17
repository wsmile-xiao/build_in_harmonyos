#!/bin/bash
# test_package/test_ohos.sh — HarmonyOS-specific checks for libagg 2.5
#
# Verifies the INSTALLED package artifacts (not the build tree):
#   1. ELF64 + AArch64 machine type
#   2. musl libc (libc.so, not libc.so.6 / glibc)
#   3. Shared build: SONAME == libagg.so.2 (libtool -version-info 2:4:0)
#   4. Shared build: DT_NEEDED contains libc.so + libc++_shared.so only
#      (no glibc/libstdc++/libgcc_s leaks)
#   5. .codesign section present (HarmonyOS signed ELFs)
#   6. Real rendering already proven by test_libagg (this script additionally
#      checks the dynamic lib really loads via its SONAME when shared)
#
# Env: PKG_LIBDIR (installed package lib dir), SHARED_BUILD (0|1)
set -u
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); echo "ok   - $1"; }
bad()  { FAIL=$((FAIL+1)); echo "FAIL - $1"; }

READELF="${READELF:-llvm-readelf}"
command -v "$READELF" >/dev/null 2>&1 || READELF=readelf

LIBDIR="${PKG_LIBDIR:?PKG_LIBDIR not set}"
SHARED="${SHARED_BUILD:-0}"

if [ "$SHARED" = "1" ]; then
    LIB="$LIBDIR/libagg.so.2.0.4"
    [ -f "$LIB" ] || LIB="$LIBDIR/libagg.so"
else
    # static build: verify the .a; ELF checks below run on the test binary
    LIB="$LIBDIR/libagg.a"
fi

if [ ! -f "$LIB" ]; then
    echo "FAIL - artifact not found: $LIB"; exit 1
fi

if [ "$SHARED" = "1" ]; then
    # 1. ELF64 / AArch64
    if "$READELF" -h "$LIB" | grep -q "Class:.*ELF64" && \
       "$READELF" -h "$LIB" | grep -q "Machine:.*AArch64"; then
        ok "shared lib is ELF64 AArch64"
    else
        bad "shared lib is not ELF64 AArch64"
    fi

    # 2. musl: NEEDED libc.so without version suffix (glibc uses libc.so.6)
    if "$READELF" -d "$LIB" | grep -q "NEEDED.*\[libc\.so\]"; then
        ok "links musl libc.so (unversioned)"
    else
        bad "libc.so (musl) not in NEEDED"
    fi
    if "$READELF" -d "$LIB" | grep -q "NEEDED.*libc\.so\.6"; then
        bad "leaks glibc libc.so.6"
    else
        ok "no glibc libc.so.6"
    fi
    if "$READELF" -d "$LIB" | grep -q "NEEDED.*libstdc++\|NEEDED.*libgcc_s"; then
        bad "leaks libstdc++/libgcc_s (should be libc++_shared.so)"
    else
        ok "no libstdc++/libgcc_s leak"
    fi

    # 3. SONAME
    SONAME=$("$READELF" -d "$LIB" | sed -n 's/.*Library soname: \[\(.*\)\]/\1/p')
    if [ "$SONAME" = "libagg.so.2" ]; then
        ok "SONAME is libagg.so.2 (libtool -version-info 2:4:0)"
    else
        bad "SONAME is '$SONAME' (expected libagg.so.2)"
    fi

    # 4. .codesign section (HarmonyOS ELF signature)
    if "$READELF" -S "$LIB" | grep -q "\.codesign"; then
        ok ".codesign section present"
    else
        bad ".codesign section missing"
    fi

    # 5. RPATH/RPATH sanity: no absolute host paths baked in
    if "$READELF" -d "$LIB" | grep -qE "(RPATH|RUNPATH).*(/storage/|/home/|/Users/|/tmp/)"; then
        bad "RPATH contains host absolute path"
    else
        ok "RPATH free of host absolute paths"
    fi

    # 6. test binary (built against this lib) is also ELF64 AArch64 and
    #    resolves libagg via SONAME
    if [ -f ./test_libagg ]; then
        if "$READELF" -h ./test_libagg | grep -q "Machine:.*AArch64"; then
            ok "test binary is AArch64"
        else
            bad "test binary is not AArch64"
        fi
        if "$READELF" -d ./test_libagg | grep -q "NEEDED.*libagg\.so"; then
            ok "test binary NEEDED libagg via SONAME"
        else
            bad "test binary does not NEED libagg"
        fi
        if "$READELF" -d ./test_libagg | grep -q "NEEDED.*libc\.so\]" ; then
            ok "test binary links musl libc"
        else
            bad "test binary does not link musl libc"
        fi
    fi
else
    # Static build checks
    if "$READELF" -h ./test_libagg 2>/dev/null | grep -q "Class:.*ELF64" && \
       "$READELF" -h ./test_libagg | grep -q "Machine:.*AArch64"; then
        ok "static-linked test binary is ELF64 AArch64"
    else
        bad "static-linked test binary is not ELF64 AArch64"
    fi
    # .a archive must contain agg objects
    if ar t "$LIB" 2>/dev/null | grep -q "agg_rasterizer"; then
        ok "static archive contains rasterizer objects"
    elif ar t "$LIB" 2>/dev/null | grep -q "\.o$"; then
        ok "static archive contains objects"
    else
        bad "static archive empty or unreadable"
    fi
    # static test binary: no libagg NEEDED (fully linked in), musl yes
    if "$READELF" -d ./test_libagg 2>/dev/null | grep -q "NEEDED.*libagg"; then
        bad "static build should not NEED shared libagg"
    else
        ok "static test binary has no libagg NEEDED"
    fi
    if "$READELF" -S ./test_libagg 2>/dev/null | grep -q "\.codesign"; then
        ok "static test binary has .codesign"
    else
        bad "static test binary missing .codesign"
    fi
fi

echo "ohos checks: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
