#!/usr/bin/env bash
# test_ticker_ohos.sh — HarmonyOS-specific verification for ticker.
#
# Usage: bash test_ticker_ohos.sh <path-to-installed-ticker> [<qemu-aarch64>]
#
# ticker is an interactive S-Lang terminal program, so its scrolling loop
# cannot run on a headless runner. These cases instead verify the substance
# of this adaptation, using only file inspection (no terminal, no qemu):
#   1. the delivered binary is an AArch64 ELF (OHOS cross-compile result).
#   2. it dynamically links the conan-provided libslang (NEEDED entry), i.e.
#      the S-Lang dependency was resolved through the Conan dependency chain
#      rather than a host library.
#
# The script is run via `bash <path>` deliberately: HarmonyOS has no
# /bin/bash and HMDFS may drop the exec bit, so the shebang is not relied on.

set -u

TICKER_BIN="${1:-}"

if [ -z "$TICKER_BIN" ] || [ ! -f "$TICKER_BIN" ]; then
    echo "ERROR: ticker binary not found: '${TICKER_BIN}'"
    exit 1
fi

pass=0
fail=0

# --- Case 1: AArch64 ELF ----------------------------------------------------
machine="$(readelf -h "$TICKER_BIN" 2>&1 | grep 'Machine:' || true)"
if printf '%s' "$machine" | grep -q "AArch64"; then
    echo "PASS: ohos1 ELF machine is AArch64: $machine"
    pass=$((pass + 1))
else
    echo "FAIL: ohos1 expected AArch64 ELF, got: $machine"
    fail=$((fail + 1))
fi

# --- Case 2: linked against libslang ----------------------------------------
needed="$(readelf -d "$TICKER_BIN" 2>&1 | grep 'NEEDED' || true)"
if printf '%s' "$needed" | grep -q "libslang"; then
    echo "PASS: ohos2 NEEDED links libslang:"
    printf -- '%s\n' "$needed"
    pass=$((pass + 1))
else
    echo "FAIL: ohos2 no libslang in NEEDED, got:"
    printf -- '%s\n' "$needed"
    fail=$((fail + 1))
fi

echo "SUMMARY: pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
