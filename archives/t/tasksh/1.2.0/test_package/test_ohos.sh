#!/usr/bin/env bash
# test_package/test_ohos.sh — HarmonyOS-specific assertions for the tasksh ELF.
#
# These are the checks that can only be made on the HarmonyOS PC target, as
# opposed to a generic CLI smoke test:
#   1. the ELF really targets aarch64-linux-ohos (EM_AARCH64 + ELF64), i.e. the
#      recipe did not silently fall back to the host x86_64 toolchain;
#   2. the ELF is a PIE (ET_DYN) — the OHOS loader refuses fixed-address
#      executables in the app sandbox;
#   3. dynamic dependency closure: every DT_NEEDED soname resolves inside the
#      OHOS runtime environment (conanrun LD_LIBRARY_PATH + system lib dirs).
#      The whole point of packaging readline/ncurses statically is that only
#      the OHOS musl libc remains at runtime — if a stray host .so sneaks in,
#      the binary loads on the build machine and dies on the device.
#   4. the binary actually executes on this OpenHarmony target.
#   5. the man page and the license shipped by the same cmake install step are
#      really in the package (the built-in help text points at `man tasksh`).
#
# usage: test_ohos.sh <tasksh_bin>
set -u

TSH="${1:-}"
fail() { echo "FAIL(HarmonyOS): $*" >&2; exit 1; }
ok()   { echo "  [ok] $*"; }

[ -n "$TSH" ] || fail "usage: test_ohos.sh <tasksh_bin>"
[ -f "$TSH" ] || fail "tasksh binary not found: $TSH"

# shellcheck source=runner.sh
. "$(dirname "$0")/runner.sh"

# --- 1. platform assertion: must be running on an OpenHarmony target ---------
# On a cross-build host there is no OHOS `param` tool and no real OHOS kernel,
# so the binary runs under qemu-aarch64. TASKSH_CROSS_EMULATED=1 is set by
# test_package/conanfile.py in that case and downgrades only this identity
# check; every other assertion below stays strict.
FULLNAME=$(param get const.ohos.fullname 2>/dev/null || true)
case "$FULLNAME" in
    OpenHarmony-*)
        ok "platform: $FULLNAME"
        ;;
    *)
        if [ "${TASKSH_CROSS_EMULATED:-}" = "1" ]; then
            echo "  [skip] T13 platform identity: cross-emulated (no OHOS param tool)"
        else
            fail "this test must run on an OpenHarmony target (got '${FULLNAME:-unknown}')"
        fi
        ;;
esac

# --- locate readelf (HNP toolchain first, then PATH) ------------------------
READELF=""
for cand in /data/service/hnp/bin/readelf /data/service/hnp/bin/llvm-readelf; do
    if [ -x "$cand" ]; then READELF="$cand"; break; fi
done
if [ -z "$READELF" ] && command -v readelf >/dev/null 2>&1; then
    READELF="$(command -v readelf)"
fi
[ -n "$READELF" ] || fail "readelf not found (HNP toolchain or PATH)"

HDR=$("$READELF" -h "$TSH" 2>/dev/null) || fail "readelf -h failed on $TSH"

# --- 2. triplet assertion: ELF64 + AArch64 ----------------------------------
echo "$HDR" | grep -q "Class:.*ELF64" \
    || fail "expected ELF64, got: $(echo "$HDR" | grep Class: || true)"
echo "$HDR" | grep -q "Machine:.*AArch64" \
    || fail "expected EM_AARCH64 (aarch64-linux-ohos), got: $(echo "$HDR" | grep Machine: || true)"
ok "ELF header: ELF64 / AArch64 (aarch64-linux-ohos)"

# --- 3. PIE assertion: ET_DYN -------------------------------------------------
# OHOS only loads position-independent executables into the app sandbox.
echo "$HDR" | grep -q "Type:.*DYN" \
    || fail "expected ET_DYN (PIE), got: $(echo "$HDR" | grep Type: || true)"
ok "ELF type: DYN (position-independent executable)"

# --- 4. dynamic dependency closure -------------------------------------------
NEEDED=$("$READELF" -d "$TSH" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/')
[ -n "$NEEDED" ] || fail "no DT_NEEDED entries found in tasksh"

# OHOS musl / HNP runtime libraries — always provided by the platform loader.
OLDIFS="$IFS"
IFS=':'
# shellcheck disable=SC2086
set -- ${LD_LIBRARY_PATH:-}
IFS="$OLDIFS"
miss=0
while IFS= read -r lib; do
    case "$lib" in
        libc.so*|libm.so*|libdl.so*|libgcc_s.so*|ld-musl*|libc++_shared.so*) continue ;;
    esac
    found=""
    for d in "$@" /system/lib64 /vendor/lib64; do
        [ -n "$d" ] || continue
        if [ -e "$d/$lib" ]; then found="$d/$lib"; break; fi
    done
    if [ -z "$found" ]; then
        echo "FAIL(HarmonyOS): NEEDED lib not resolvable at runtime: $lib"
        miss=1
    fi
done <<EOF
$NEEDED
EOF
[ "$miss" -eq 0 ] || fail "dynamic dependencies not closed on OHOS"
ok "dynamic dependency closure: $(echo "$NEEDED" | grep -c . ) DT_NEEDED entrie(s) all resolve"

# --- 5. static link assertion: readline/ncurses must NOT be runtime deps ----
# If they showed up here, the static link silently degraded to shared and the
# binary would need extra .so files on the device.
echo "$NEEDED" | grep -q "readline" && fail "libreadline leaked into DT_NEEDED (expected static link)"
echo "$NEEDED" | grep -q "ncurses" && fail "libncurses leaked into DT_NEEDED (expected static link)"
ok "readline/ncurses are statically linked (absent from DT_NEEDED)"

# --- 6. run-time confirmation on the OHOS target ----------------------------
VER=$(tsh_run --version) || fail "tasksh --version failed on OHOS"
[ "$VER" = "1.2.0" ] || fail "tasksh --version printed '$VER' on OHOS, expected '1.2.0'"
ok "tasksh executes on OpenHarmony and reports 1.2.0"

# --- 7. the shipped documentation is installed alongside the binary ---------
# tasksh's man page and docs come from the same CMake install step as bin/;
# a partial install would silently drop the `tasksh.1` referenced by the
# built-in help text ("Run 'man tasksh' from your shell prompt").
PKGROOT=$(dirname "$(dirname "$TSH")")
[ -f "$PKGROOT/share/man/man1/tasksh.1" ] \
    || fail "man page not installed at $PKGROOT/share/man/man1/tasksh.1"
[ -f "$PKGROOT/share/doc/tasksh/COPYING" ] \
    || fail "license not installed at $PKGROOT/share/doc/tasksh/COPYING"
ok "man page + license installed under share/"

echo "=== HarmonyOS-specific assertions passed ==="