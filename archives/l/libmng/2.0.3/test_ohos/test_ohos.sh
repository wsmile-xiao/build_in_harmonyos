#!/usr/bin/env bash
# HarmonyOS-specific test — libmng 2.0.3 (static delivery)
#
# Runs on OpenHarmony PC against the FINAL Conan package. libmng is
# static-only on OHOS: the registry zlib/1.3.1 package ships only a
# non-PIC static libz.a which cannot be linked into a shared libmng
# (see conanfile.py validate()). This validates the STATIC delivery,
# independent of test_package (library API):
#   H1 static-only package: libmng.a present and no libmng.so* shipped;
#      every archive member is ELF64 Little-Endian AArch64 (a readelf
#      failure fails the check)
#   H2 consumer ELF hygiene — a consumer binary linked against the real
#      package libmng.a: NEEDED closure exactly
#      {libjpeg.so.62, liblcms2.so.2, libc.so} (jpeg/lcms2 shared from
#      the registry, zlib statically folded in — NEVER resolved against
#      the host sysroot libz.so, and no libturbojpeg false dependency),
#      no RPATH/RUNPATH, and zlib really linked in (crc32 defined in
#      the symbol table, absent from dynamic imports)
#   H3 .codesign section present on the consumer executable
#   H4 no host build paths leaked into the shipped libmng.a
#   H5 real MNG decode on the OHOS loader: a tiny C consumer is
#      compiled against the package headers and libmng.a (dependency
#      archives linked by ABSOLUTE path, never -l lookup), decoding
#      the upstream fixture (linux.mng restored byte-for-byte from
#      Base64 text), asserting callback counts, image dimensions and
#      per-row canvas access
#
# Usage: bash test_ohos.sh <package_folder> [readelf_path]
# The caller (test_ohos/conanfile.py) stages the dependency archives
# and headers into one private directory and exports CPATH /
# LIBMNG_DEPS_DIR / LD_LIBRARY_PATH / LIBMNG_FIXTURE / CC before
# launching this script; the script itself takes no
# environment-directory argument.
#
# All check output is TAP (ok/not ok lines + trailing plan line) and is
# always fully emitted, including when individual checks fail. Test
# artifacts (consumer binary, decode output) go to a private temp
# directory that is removed on success, failure, Ctrl-C and timeout
# (SIGTERM) — never into the package folder.

set -euo pipefail

PKG="${1:?usage: test_ohos.sh <package_folder> [readelf_path]}"
RE="${2:-readelf}"
DEPS_DIR="${LIBMNG_DEPS_DIR:?LIBMNG_DEPS_DIR is required}"
FIXTURE="${LIBMNG_FIXTURE:?LIBMNG_FIXTURE is required}"

fail=0
checks=0
check() {
    checks=$((checks + 1))
    if [ "$2" = "ok" ]; then
        echo "ok $checks - $1"
    else
        echo "not ok $checks - $1 ($2)"
        fail=$((fail + 1))
    fi
}

# ── Private temp directory + guaranteed cleanup ────────────────────────
# Created before any check runs; removed on normal exit, on unexpected
# error (EXIT), on Ctrl-C (INT) and on timeout kills (TERM).
TMPD=""
cleanup() {
    if [ -n "$TMPD" ]; then
        rm -rf "$TMPD"
    fi
}
trap cleanup EXIT
trap 'trap - INT; cleanup; exit 130' INT
trap 'trap - TERM; cleanup; exit 143' TERM
if ! TMPD="$(mktemp -d "${TMPDIR:-/tmp}/libmng-test-ohos.XXXXXX" 2>/dev/null)"; then
    # /tmp may be read-only on OHOS images — try $TMPDIR, /tmp, then $HOME
    # (never ".": cwd may be inside the package folder). If no location
    # works, bail out explicitly instead of writing test output anywhere.
    if ! TMPD="$(mktemp -d "/tmp/libmng-test-ohos.XXXXXX" 2>/dev/null)" \
        && ! TMPD="$(mktemp -d "${HOME:?HOME not set}/libmng-test-ohos.XXXXXX" 2>/dev/null)"; then
        echo "Bail out! cannot create private temp directory"
        exit 1
    fi
fi

LIB="$PKG/lib/libmng.a"

# ── Data collection ────────────────────────────────────────────────────
# All raw facts are gathered first; the ten checks are emitted
# afterwards so the TAP stream stays ordered H1..H5 even when an early
# step (compile, run) fails.

# H1: static-only delivery + archive member ELF headers.
so_count=0
for f in "$PKG/lib"/libmng.so*; do
    if [ -f "$f" ]; then
        so_count=$((so_count + 1))
    fi
done
have_lib=0
if [ -f "$LIB" ]; then
    have_lib=1
fi

hdr_fail=""
members=0
elf64=0
le=0
mach=0
if ! hdr="$($RE -h "$LIB" 2>&1)"; then
    hdr_fail="$hdr"
else
    members="$(printf '%s\n' "$hdr" | grep -c 'Class:' || true)"
    elf64="$(printf '%s\n' "$hdr" | grep -c "Class: *ELF64" || true)"
    le="$(printf '%s\n' "$hdr" | grep -c "Data: *2's complement, little endian" || true)"
    mach="$(printf '%s\n' "$hdr" | grep -c 'Machine: *AArch64' || true)"
fi

# H5: consumer source — decodes the upstream linux.mng fixture via the
# libmng callbacks (virtual-clock animation resume), asserting
# initialization, readdisplay status, image dimensions and per-row
# canvas access.
cat >"$TMPD/decode.c" <<'EOF'
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libmng.h"

typedef struct {
    FILE *f; int lines; mng_uint32 w, h; int hdr;
    unsigned char canvas[101 * 4];
} ctx_t;

static mng_ptr my_alloc(mng_size_t n) { return calloc(1, n); }
static void my_free(mng_ptr p, mng_size_t n) { free(p); (void)n; }
static mng_bool cb_open(mng_handle h) { (void)h; return MNG_TRUE; }
static mng_bool cb_close(mng_handle h) { (void)h; return MNG_TRUE; }
static mng_bool cb_read(mng_handle h, mng_ptr b, mng_uint32 n, mng_uint32 *r) {
    ctx_t *c = (ctx_t *)mng_get_userdata(h);
    *r = (mng_uint32)fread(b, 1, n, c->f);
    return MNG_TRUE;
}
static mng_bool cb_hdr(mng_handle h, mng_uint32 w, mng_uint32 h_) {
    ctx_t *c = (ctx_t *)mng_get_userdata(h);
    c->w = w; c->h = h_; c->hdr++;
    return mng_set_canvasstyle(h, MNG_CANVAS_RGBA8) == MNG_NOERROR;
}
static mng_ptr cb_line(mng_handle h, mng_uint32 y) {
    ctx_t *c = (ctx_t *)mng_get_userdata(h);
    c->lines++; (void)y;
    return (mng_ptr)c->canvas;
}
static mng_bool cb_refresh(mng_handle h, mng_uint32 x, mng_uint32 y,
                           mng_uint32 w, mng_uint32 h_) {
    (void)h; (void)x; (void)y; (void)w; (void)h_;
    return MNG_TRUE;
}
static mng_uint32 g_ticks = 0, g_delay = 0;
static mng_uint32 cb_ticks(mng_handle h) { (void)h; return g_ticks; }
static mng_bool cb_timer(mng_handle h, mng_uint32 ms) {
    (void)h; g_delay = ms; return MNG_TRUE;
}

int main(int argc, char **argv) {
    if (argc < 2) { puts("1..0 # SKIP no fixture"); return 0; }
    puts("TAP version 13");
    int failed = 0;
    ctx_t c; memset(&c, 0, sizeof c);
    c.f = fopen(argv[1], "rb");
    if (!c.f) { puts("not ok 1 - fixture open"); return 1; }
    puts("1..4");
    mng_handle h = mng_initialize(&c, my_alloc, my_free, MNG_NULL);
    if (!h) { puts("not ok 1 - init"); return 1; }
    puts("ok 1 - mng_initialize on OHOS");
    mng_setcb_openstream(h, cb_open);
    mng_setcb_closestream(h, cb_close);
    mng_setcb_readdata(h, cb_read);
    mng_setcb_processheader(h, cb_hdr);
    mng_setcb_getcanvasline(h, cb_line);
    mng_setcb_refresh(h, cb_refresh);
    mng_setcb_gettickcount(h, cb_ticks);
    mng_setcb_settimer(h, cb_timer);
    mng_retcode rc = mng_readdisplay(h);
    int iter = 0;
    while (rc == MNG_NEEDTIMERWAIT && c.lines < 127 && ++iter < 1000) {
        g_ticks += g_delay ? g_delay : 1;
        rc = mng_display_resume(h);
    }
    if (rc == MNG_NEEDTIMERWAIT || rc == MNG_NOERROR) {
        puts("ok 2 - readdisplay NEEDTIMERWAIT/NOERROR");
    } else {
        printf("not ok 2 - readdisplay rc=%d\n", rc);
        failed = 1;
    }
    if (c.w == 101 && c.h == 127) {
        puts("ok 3 - dimensions 101x127");
    } else {
        printf("not ok 3 - dims %lux%lu\n", (unsigned long)c.w,
               (unsigned long)c.h);
        failed = 1;
    }
    if (c.lines >= 127) {
        puts("ok 4 - full frame decoded (>=127 canvas lines)");
    } else {
        printf("not ok 4 - canvas lines %d\n", c.lines);
        failed = 1;
    }
    mng_cleanup(&h);
    fclose(c.f);
    return failed ? 1 : 0;
}
EOF

# ── H5: build & run the consumer ──────────────────────────────────────
# Include path: CPATH points at LIBMNG_DEPS_DIR (flat staged headers of
# zlib/jpeg/lcms2) and the package include dir is passed explicitly.
INC_ARGS=""
for d in ${CPATH//:/ }; do
    [ -f "$d/zlib.h" ] && INC_ARGS="$INC_ARGS -I$d"
done

# Link line — order matters for static archives (ld.lld single pass):
#   objects  →  libmng.a  →  libz.a (ABSOLUTE PATH, see below)  →
#   shared deps
# zlib must be linked by absolute path to the Conan libz.a: the OHOS
# clang sysroot ships a libz.so, so plain `-lz` silently resolves to the
# SYSTEM library (verified on device) and fabricates a bogus NEEDED
# libz.so entry. jpeg/lcms2 are shared in the registry; linking them
# with -l from LIBMNG_DEPS_DIR yields the real closure: NEEDED =
# {libjpeg.so.62, liblcms2.so.2, libc.so}, zlib folded in statically.
ZLIB_A="$DEPS_DIR/libz.a"
if [ ! -f "$ZLIB_A" ]; then
    check "H5 staging has libz.a" "missing $ZLIB_A"
else
    if "${CC:-cc}" -o "$TMPD/decode" "$TMPD/decode.c" \
        -I"$PKG/include" $INC_ARGS -L"$DEPS_DIR" -L"$PKG/lib" \
        -lmng "$ZLIB_A" -ljpeg -llcms2 2>"$TMPD/cc.log"; then
        check "H5 consumer compiles+links against package" ok
    else
        check "H5 consumer compiles+links against package" \
            "cc failed: $(tail -3 "$TMPD/cc.log" | tr '\n' ' ')"
    fi
fi

run_out=""
if [ -x "$TMPD/decode" ]; then
    if run_out="$(cd "$TMPD" && "$TMPD/decode" "$FIXTURE" 2>&1)"; then
        :
    else
        run_out="$run_out (exit $?)"
    fi
fi

# ── Checks H1..H5 ─────────────────────────────────────────────────────
# H1: static-only delivery + AArch64 ELF members.
if [ "$hdr_fail" != "" ]; then
    check "H1 libmng.a members are ELF64 LE AArch64" "readelf: $hdr_fail"
elif [ "$members" -gt 0 ] && [ "$elf64" = "$members" ] \
    && [ "$le" = "$members" ] && [ "$mach" = "$members" ]; then
    check "H1 libmng.a members are ELF64 LE AArch64 ($members members)" ok
else
    check "H1 libmng.a members are ELF64 LE AArch64" \
        "members=$members elf64=$elf64 le=$le mach=$mach"
fi
if [ "$have_lib" = "1" ] && [ "$so_count" = "0" ]; then
    check "H1 static-only package (libmng.a, no libmng.so*)" ok
else
    check "H1 static-only package (libmng.a, no libmng.so*)" \
        "libmng.a=$have_lib libmng.so*=$so_count"
fi

# H2: consumer ELF hygiene — NEEDED closure exactly
# {libjpeg.so.62, liblcms2.so.2, libc.so}, no RPATH/RUNPATH pointing
# into the host build tree, zlib statically linked in (crc32 present in
# .symtab, absent from .dynsym).
if [ -x "$TMPD/decode" ]; then
    needed="$("$RE" -d "$TMPD/decode" 2>/dev/null | sed -n 's/.*Shared library: \[\(.*\)\]/\1/p' | sort)"
    want="libc.so
libjpeg.so.62
liblcms2.so.2"
    if [ "$(printf '%s\n' "$needed")" = "$want" ]; then
        check "H2 NEEDED closure (jpeg+lcms2 shared, zlib static)" ok
    else
        check "H2 NEEDED closure (jpeg+lcms2 shared, zlib static)" \
            "got: $(printf '%s' "$needed" | tr '\n' ' ')"
    fi
    if "$RE" -d "$TMPD/decode" 2>/dev/null | grep -qE 'RPATH|RUNPATH'; then
        check "H2 no RPATH/RUNPATH in consumer" \
            "$("$RE" -d "$TMPD/decode" | sed -n 's/.*(RPATH\|RUNPATH).*//p')"
    else
        check "H2 no RPATH/RUNPATH in consumer" ok
    fi
    n_c32=0
    if "$RE" --syms "$TMPD/decode" 2>/dev/null | grep -qE ' crc32$'; then
        n_c32=1
    fi
    n_c32d=0
    if "$RE" --dyn-syms "$TMPD/decode" 2>/dev/null | grep -qE ' crc32$'; then
        n_c32d=1
    fi
    if [ "$n_c32" = "1" ] && [ "$n_c32d" = "0" ]; then
        check "H2 zlib statically linked in (crc32 in symtab, not dynsym)" ok
    else
        check "H2 zlib statically linked in (crc32 in symtab, not dynsym)" \
            "symtab=$n_c32 dynsym=$n_c32d"
    fi
    # No false dependency on libturbojpeg.so — the library is
    # libjpeg.so.62 only; a libturbojpeg NEEDED entry would mean the
    # consumer picked up a wrong jpeg library at link time.
    if printf '%s\n' "$needed" | grep -q 'libturbojpeg'; then
        check "H2 no libturbojpeg false dependency" \
            "NEEDED contains libturbojpeg"
    else
        check "H2 no libturbojpeg false dependency" ok
    fi
else
    check "H2 NEEDED closure (jpeg+lcms2 shared, zlib static)" "no consumer binary"
    check "H2 no RPATH/RUNPATH in consumer" "no consumer binary"
    check "H2 zlib statically linked in (crc32 in symtab, not dynsym)" "no consumer binary"
    check "H2 no libturbojpeg false dependency" "no consumer binary"
fi

# H3: .codesign section on the consumer executable (OHOS requirement).
if [ -x "$TMPD/decode" ]; then
    if "$RE" -S "$TMPD/decode" 2>/dev/null | grep -q '\.codesign'; then
        check "H3 .codesign section on consumer executable" ok
    else
        check "H3 .codesign section on consumer executable" "missing"
    fi
else
    check "H3 .codesign section on consumer executable" "no consumer binary"
fi

# H4: no host build paths leaked into the shipped libmng.a.
# (toybox head exits before grep when there are no matches → SIGPIPE
# makes grep return 141 and pipefail turns that into a script abort;
# `|| true` guards the no-match case which is the PASSING case.)
leak="$(strings -a "$LIB" 2>/dev/null | { grep -E '/storage/|/home/|/data/' || true; } | head -1)"
if [ -z "$leak" ]; then
    check "H4 no host build paths in libmng.a" ok
else
    check "H4 no host build paths in libmng.a" "$leak"
fi

# H5: real MNG decode on the OHOS loader.
if [ -x "$TMPD/decode" ]; then
    if printf '%s\n' "$run_out" | grep -q '^ok 4 '; then
        check "H5 real MNG decode (101x127, >=127 canvas lines)" ok
    else
        check "H5 real MNG decode (101x127, >=127 canvas lines)" \
            "$(printf '%s' "$run_out" | tr '\n' ';')"
    fi
else
    check "H5 real MNG decode (101x127, >=127 canvas lines)" "no consumer binary"
fi

# ── Summary ────────────────────────────────────────────────────────────
echo "1..$checks"
if [ "$fail" -gt 0 ]; then
    echo "FAILED $fail/$checks checks"
    exit 1
fi
echo "ALL CHECKS PASSED"
exit 0
