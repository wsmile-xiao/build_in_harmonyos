#!/usr/bin/env bash
# HarmonyOS-specific test — libsigc++ 2.12.2
#
# Runs on OpenHarmony PC against the FINAL Conan package. Independently
# verifies platform delivery aspects the consumer test does not cover:
#   H1  ELF64 Little-Endian AArch64 class/data/machine for the shipped
#       library and the compiled consumer (readelf failure = FAIL)
#   H2  dynamic section: SONAME libsigc-2.0.so.0, no host RPATH/RUNPATH
#   H3  NEEDED closure: consumer needs the SONAME; library needs only
#       the system loader-provided libc++/libc (musl)
#   H4  consumer ELF requests the musl-aarch64 dynamic loader
#   H5  .codesign section present on the shipped library and consumer
#   H6  no host build paths leaked into binaries (strings scan)
#   H7  real signal/slot execution on OpenHarmony PC: the consumer runs
#       with the packaged library on LD_LIBRARY_PATH and its 20 API
#       assertions (signal/slot, return values, disconnect, trackable
#       lifetime, member binding, exception path) all pass
#
# Usage: test_ohos.sh <package_folder> <consumer_executable> [readelf_path]
# The caller (test_ohos/conanfile.py) compiles the consumer against the
# tested package and passes its path; it also exports LD_LIBRARY_PATH.
#
# All check output is TAP (ok/not ok lines + trailing plan line) and is
# always fully emitted, including when individual checks fail. The
# consumer's stdout/stderr go to a private temp directory that is removed
# on success, failure, Ctrl-C and timeout (SIGTERM) — never into the
# package folder.

set -euo pipefail

PKG="${1:?usage: test_ohos.sh <package_folder> <consumer_executable> [readelf_path]}"
CONSUMER="${2:?usage: test_ohos.sh <package_folder> <consumer_executable> [readelf_path]}"
RE="${3:-readelf}"

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
TMPD=""
cleanup() {
    if [ -n "$TMPD" ]; then
        rm -rf "$TMPD"
    fi
}
trap cleanup EXIT
trap 'trap - INT; cleanup; exit 130' INT
trap 'trap - TERM; cleanup; exit 143' TERM
if ! TMPD="$(mktemp -d "${TMPDIR:-/tmp}/libsigc2-test-ohos.XXXXXX" 2>/dev/null)"; then
    # /tmp may be read-only on OHOS images — try $TMPDIR, /tmp, then $HOME
    # (never ".": cwd may be inside the package folder). If no location
    # works, bail out explicitly instead of writing test output anywhere.
    if ! TMPD="$(mktemp -d "/tmp/libsigc2-test-ohos.XXXXXX" 2>/dev/null)" \
        && ! TMPD="$(mktemp -d "${HOME:?HOME not set}/libsigc2-test-ohos.XXXXXX" 2>/dev/null)"; then
        echo "Bail out! cannot create private temp directory"
        exit 1
    fi
fi

VARIANT="${4:-shared}"
case "$VARIANT" in
    shared)
        LIB="$PKG/lib/libsigc-2.0.so.0.0.0"
        SONAME_ALIAS="$PKG/lib/libsigc-2.0.so.0"
        LINKER_ALIAS="$PKG/lib/libsigc-2.0.so"
        ;;
    static)
        LIB="$PKG/lib/libsigc-2.0.a"
        SONAME_ALIAS=""
        LINKER_ALIAS=""
        ;;
    *)
        echo "usage: test_ohos.sh <package_folder> <consumer> [readelf] [shared|static]" >&2
        exit 2
        ;;
esac

# Shared-only checks (SONAME/RPATH-on-so/aliases/NEEDED closure) do not
# apply to a static delivery; report them as skipped TAP diagnostics so
# the check numbering stays identical across variants.
skip() {
    checks=$((checks + 1))
    echo "ok $checks - $1 # skip static delivery"
}

IS_SHARED=0
[ "$VARIANT" = "shared" ] && IS_SHARED=1

# ── H1: ELF64 / Little-Endian / AArch64, verified per artifact ────────
# (shared: library .so + consumer; static: consumer only — the archive
# itself is not an ELF object, so no ELF header check applies to it)
if [ "$IS_SHARED" = "1" ]; then
    H1_ARTIFACTS="$LIB $CONSUMER"
else
    H1_ARTIFACTS="$CONSUMER"
fi
for f in $H1_ARTIFACTS; do
    name="$(basename "$f")"
    if hdr="$($RE -h "$f" 2>&1)"; then
        class="$(printf '%s\n' "$hdr" | sed -n 's/^ *Class: *//p')"
        data="$(printf '%s\n' "$hdr" | sed -n 's/^ *Data: *//p')"
        mach="$(printf '%s\n' "$hdr" | sed -n 's/^ *Machine: *//p')"
        if [ "$class" = "ELF64" ] \
            && [ "$data" = "2's complement, little endian" ] \
            && [ "$mach" = "AArch64" ]; then
            check "H1 $name is ELF64 Little-Endian AArch64 (machine: $mach)" ok
        else
            check "H1 $name is ELF64 Little-Endian AArch64" \
                "class=$class data=$data machine=$mach"
        fi
    else
        err="${hdr%%$'\n'*}"
        check "H1 $name is ELF64 Little-Endian AArch64" "readelf failed: $err"
    fi
done

# ── H2: SONAME + no host RPATH ────────────────────────────────────────
if [ "$IS_SHARED" = "1" ]; then
    dyn_lib="$($RE -d "$LIB" 2>&1 || true)"
else
    dyn_lib=""
fi
dyn_con="$($RE -d "$CONSUMER" 2>&1 || true)"

if [ "$IS_SHARED" = "1" ]; then
    son="$(printf '%s\n' "$dyn_lib" | grep 'SONAME' | sed 's/.*\[\(.*\)\]/\1/' || true)"
    [ "$son" = "libsigc-2.0.so.0" ] && check "H2 library SONAME is libsigc-2.0.so.0" ok \
        || check "H2 library SONAME is libsigc-2.0.so.0" "got: $son"
else
    skip "H2 library SONAME is libsigc-2.0.so.0"
fi

for f in "$LIB" "$CONSUMER"; do
    name="$(basename "$f")"
    dyn="$dyn_lib"
    [ "$f" = "$CONSUMER" ] && dyn="$dyn_con"
    if [ "$f" != "$CONSUMER" ] && [ "$IS_SHARED" = "0" ]; then
        skip "H2 $name has no RPATH/RUNPATH"
        continue
    fi
    rp="$(printf '%s\n' "$dyn" | grep -E 'RPATH|RUNPATH' || true)"
    [ -z "$rp" ] && check "H2 $name has no RPATH/RUNPATH" ok \
        || check "H2 $name has no RPATH/RUNPATH" "$rp"
done

# SONAME and linker aliases must exist next to the versioned real file
if [ "$IS_SHARED" = "1" ]; then
    [ -f "$SONAME_ALIAS" ] && check "H2 SONAME alias libsigc-2.0.so.0 is materialized" ok \
        || check "H2 SONAME alias libsigc-2.0.so.0 is materialized" "missing"
    [ -f "$LINKER_ALIAS" ] && check "H2 linker alias libsigc-2.0.so is materialized" ok \
        || check "H2 linker alias libsigc-2.0.so is materialized" "missing"
else
    skip "H2 SONAME alias libsigc-2.0.so.0 is materialized"
    skip "H2 linker alias libsigc-2.0.so is materialized"
fi

# ── H3: NEEDED closure ─────────────────────────────────────────────────
# the consumer must depend on the library through its SONAME (shared
# delivery only; a static delivery folds the symbols into the consumer)
if [ "$IS_SHARED" = "1" ]; then
    printf '%s\n' "$dyn_con" | grep 'NEEDED.*libsigc-2\.0\.so\.0' >/dev/null \
        && check "H3 consumer NEEDED includes libsigc-2.0.so.0" ok \
        || check "H3 consumer NEEDED includes libsigc-2.0.so.0" "missing"
else
    skip "H3 consumer NEEDED includes libsigc-2.0.so.0"
fi

# the library itself must only need system-provided C++ runtime libs;
# a host path in NEEDED would leak build-machine state
bad_needed="$(printf '%s\n' "$dyn_lib" | grep '(NEEDED)' \
    | sed 's/.*\[\(.*\)\].*/\1/' | grep -E '^/|^\.\./' || true)"
[ -z "$bad_needed" ] && check "H3 library NEEDED has no absolute or ../ paths" ok \
    || check "H3 library NEEDED has no absolute or ../ paths" "$bad_needed"

# and it must rely on the system musl libc++ (libc++_shared.so), not a
# vendored copy bundled into the package
if [ "$IS_SHARED" = "1" ]; then
    self_contained="$(printf '%s\n' "$dyn_lib" | grep -c 'NEEDED.*libc++_shared' || true)"
    vendored="$(printf '%s\n' "$dyn_lib" | grep -c 'NEEDED.*lib/\|NEEDED.*\.\/' || true)"
    [ "$self_contained" = "1" ] && [ "$vendored" = "0" ] \
        && check "H3 library relies on system libc++ (libc++_shared.so NEEDED, no vendored copy)" ok \
        || check "H3 library relies on system libc++ (libc++_shared.so NEEDED, no vendored copy)" \
            "libc++_shared NEEDED count=$self_contained, vendored-paths count=$vendored"
else
    skip "H3 library relies on system libc++ (libc++_shared.so NEEDED, no vendored copy)"
fi

# ── H4: musl dynamic loader ────────────────────────────────────────────
interp="$($RE -l "$CONSUMER" 2>/dev/null | grep 'Requesting program interpreter' \
    | sed 's/.*interpreter: \(.*\)\]/\1/' || true)"
[ "$interp" = "/lib/ld-musl-aarch64.so.1" ] \
    && check "H4 consumer requests the musl-aarch64 loader" ok \
    || check "H4 consumer requests the musl-aarch64 loader" "got: $interp"

# ── H5: .codesign section ─────────────────────────────────────────────
for f in "$LIB" "$CONSUMER"; do
    name="$(basename "$f")"
    if [ "$f" != "$CONSUMER" ] && [ "$IS_SHARED" = "0" ]; then
        skip "H5 $name carries .codesign section"
        continue
    fi
    n="$($RE -SW "$f" 2>/dev/null | grep -c 'codesign' || true)"
    [ "$n" -ge 1 ] && check "H5 $name carries .codesign section" ok \
        || check "H5 $name carries .codesign section" "count=$n"
done

# ── H6: no host build paths ───────────────────────────────────────────
for f in "$LIB" "$CONSUMER"; do
    name="$(basename "$f")"
    n="$(strings "$f" 2>/dev/null | grep -cE '/home/|/tmp/|storage/Users/' || true)"
    [ "$n" = "0" ] && check "H6 $name has no host paths" ok \
        || check "H6 $name has no host paths" "count=$n"
done

# ── H7: real signal/slot execution on OpenHarmony PC ──────────────────
# The consumer exercises signal/slot, return values, connection
# disconnect, trackable lifetime, member-function binding, bound slots,
# lambda slots and the exception path (20 assertions); it exits 0 only
# when every assertion passed.
OUT="$TMPD/consumer.out"
ERRF="$TMPD/consumer.err"
rc=0
if [ -x "$CONSUMER" ]; then
    "$CONSUMER" > "$OUT" 2> "$ERRF" || rc=$?
else
    rc=127
fi
[ "$rc" = "0" ] && check "H7 consumer signal/slot suite passed on OHOS (exit 0)" ok \
    || check "H7 consumer signal/slot suite passed on OHOS" "exit=$rc"
if [ "$rc" != "0" ] && [ -s "$ERRF" ]; then
    # surface the consumer's own failure message for diagnosis (TAP comments)
    sed -n '1,5p' "$ERRF" | sed 's/^/# consumer stderr: /'
fi

echo "1..$checks"
if [ "$fail" -gt 0 ]; then
    echo "# FAILED $fail/$checks"
    exit 1
fi
echo "# passed $checks/$checks"
