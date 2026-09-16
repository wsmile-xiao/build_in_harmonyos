#!/bin/bash
# test_ohos.sh — libblastrampoline OHOS platform invariants
# Usage: test_ohos.sh <build_folder>
#
# Verifies the packaged library for HarmonyOS PC (aarch64, musl):
#   1. ELF machine is AArch64
#   2. SONAME is libblastrampoline.so.5
#   3. NEEDED contains libc.so (musl; dlopen lives in libc) and nothing else
#   4. lbt_forward/lbt_get_config exported; aarch64 trampolines functional
#   5. .codesign section present (OHOS toolchain artifact)
#   6. Real dynamic loading: the consumer test already ran through lbt_forward
#      (dlopen of fake backends); here we additionally verify the library
#      itself is dlopen-able standalone.
set -euo pipefail

BUILD_FOLDER="${1:?usage: test_ohos.sh <build_folder>}"
FAILED=0
check() { # check <cond> <msg>
    # Disable pipefail inside eval: grep -q closing the readelf pipe early
    # (SIGPIPE, exit 141) must not be treated as a failed check.
    local _rc=0
    ( set +e; set +o pipefail; eval "$1" ) || _rc=$?
    if [ "$_rc" -eq 0 ]; then echo "PASS(OHOS): $2"; else echo "FAIL(OHOS): $2"; FAILED=1; fi
}

# locate the packaged library via conanbindirs-style search
LBT=""
for d in "$BUILD_FOLDER" "$BUILD_FOLDER/Release" "$BUILD_FOLDER/Debug"; do
    for f in "$d/libblastrampoline.so.5" "$d"/*.so*; do
        [ -f "$f" ] || continue
        case "$(basename "$f")" in
            libblastrampoline.so*) LBT="$f"; break 2 ;;
        esac
    done
done
if [ -z "$LBT" ] && [ -n "${CONAN_LIBS:-}" ]; then
    # fallback: glob in the conan package lib dir
    for f in "$CONAN_LIBS"/libblastrampoline.so*; do
        [ -f "$f" ] && { LBT="$f"; break; }
    done
fi
check '[ -n "$LBT" ]' "libblastrampoline.so.5 found (searched $BUILD_FOLDER, LBT=$LBT)"
[ -n "$LBT" ] || { echo "cannot continue without the library"; exit 1; }

echo "-- library: $LBT"

# 1. AArch64 ELF
check 'readelf -h "$LBT" | grep -q "Machine:.*AArch64"' "ELF machine is AArch64"

# 2. SONAME
check 'readelf -d "$LBT" | grep -q "SONAME.*libblastrampoline.so.5"' "SONAME is libblastrampoline.so.5"

# 3. NEEDED: only libc.so (musl merged libdl; backends are dlopened at runtime)
check '[ "$(readelf -d "$LBT" | grep -c NEEDED)" = "1" ]' "exactly one NEEDED entry"
check 'readelf -d "$LBT" | grep -q "NEEDED.*libc.so"' "NEEDED libc.so (musl)"

# 4. key exported symbols
check 'readelf --dyn-syms "$LBT" | grep -q "lbt_forward"' "lbt_forward exported"
check 'readelf --dyn-syms "$LBT" | grep -q "lbt_get_config"' "lbt_get_config exported"
check 'readelf --dyn-syms "$LBT" | grep -q " dgemm_$"' "dgemm_ trampoline exported"
check 'readelf --dyn-syms "$LBT" | grep -q " dgemm_64_$"' "dgemm_64_ trampoline exported"
check 'readelf --dyn-syms "$LBT" | grep -q "lbt_get_forward"' "lbt_get_forward exported"

# 5. .codesign section (OHOS toolchain generates it)
check 'readelf -SW "$LBT" | grep -q "\.codesign"' ".codesign section present"

# 6. real dynamic loading of the library itself (musl dlopen).
#    The dlopen_probe helper is compiled with this priority: $CC when set
#    (never overridden), else clang from PATH; no implicit gcc fallback.
#    The probe is arch-checked (ELF64 AArch64) before it is executed.
cat > "$BUILD_FOLDER/dlopen_probe.c" <<'EOF'
#include <dlfcn.h>
#include <stdio.h>
int main(int argc, char **argv) {
    void *h = dlopen(argv[1], RTLD_NOW);
    if (!h) { fprintf(stderr, "dlopen failed: %s\n", dlerror()); return 1; }
    void (*fwd)(void) = (void (*)(void))dlsym(h, "lbt_get_config");
    if (!fwd) { fprintf(stderr, "lbt_get_config not found\n"); return 1; }
    printf("dlopen_probe: lbt_get_config @ %p\n", fwd);
    return 0;
}
EOF
# Probe artifacts are removed on every exit path (failure diagnostics below
# exit directly; normal completion falls through to the summary).
cleanup_probe() {
    rm -f "$BUILD_FOLDER/dlopen_probe.c" "$BUILD_FOLDER/dlopen_probe"
}
trap cleanup_probe EXIT
# Compiler selection, in priority order:
#   1. $CC when non-empty (may carry arguments, e.g. "clang -O2" or a
#      cross-compiler wrapper); it is never overridden by anything below.
#   2. clang from PATH, only when $CC is empty.
# No implicit gcc fallback: a host-architecture compiler would emit a probe
# that cannot load the packaged aarch64 library; fail loudly instead.
CC_CMD=()
if [ -n "${CC:-}" ]; then
    # CC may contain arguments: split into a bash array so each word is
    # passed as its own argv entry instead of one long nonexistent filename.
    read -r -a CC_CMD <<<"$CC"
elif command -v clang >/dev/null 2>&1; then
    CC_CMD=(clang)
fi
if [ "${#CC_CMD[@]}" -eq 0 ]; then
    echo "FAIL(OHOS): no usable target C compiler: CC='${CC:-}' and no clang in PATH" >&2
    echo "  export CC=<aarch64 OHOS compiler> and re-run" >&2
    cleanup_probe
    exit 1
fi
if ! command -v "${CC_CMD[0]}" >/dev/null 2>&1; then
    echo "FAIL(OHOS): CC='${CC:-}' names non-executable compiler '${CC_CMD[0]}'" >&2
    cleanup_probe
    exit 1
fi
CC_DESC="${CC:-${CC_CMD[*]}}"
if ! "${CC_CMD[@]}" -o "$BUILD_FOLDER/dlopen_probe" "$BUILD_FOLDER/dlopen_probe.c" -ldl; then
    echo "FAIL(OHOS): dlopen_probe compilation failed (CC='$CC_DESC')" >&2
    cleanup_probe
    exit 1
fi
# The probe itself must be ELF64 AArch64: a host/wrong-architecture compiler
# would produce a probe that can never load the packaged library. Capture
# readelf output once (no pipe: grep -q SIGPIPE under pipefail).
PROBE_ELF="$(readelf -h "$BUILD_FOLDER/dlopen_probe" 2>/dev/null || true)"
if ! grep -q 'Class:.*ELF64' <<<"$PROBE_ELF" || ! grep -q 'Machine:.*AArch64' <<<"$PROBE_ELF"; then
    echo "FAIL(OHOS): dlopen_probe is not ELF64 AArch64 (CC='$CC_DESC' is a host/wrong-arch compiler); refusing to execute it" >&2
    cleanup_probe
    exit 1
fi
check '"$BUILD_FOLDER/dlopen_probe" "$LBT" >/dev/null 2>&1' "standalone dlopen(lbt) + dlsym(lbt_get_config) works"

if [ "$FAILED" -ne 0 ]; then
    echo "test_ohos.sh: FAILURES detected"
    exit 1
fi
echo "test_ohos.sh: all OHOS platform invariants passed"
