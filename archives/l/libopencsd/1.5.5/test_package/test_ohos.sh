#!/bin/bash
# libopencsd HarmonyOS-specific test (rule12).
#
# Verifies, against the packaged artifact, the integration points that are
# specific to the HarmonyOS build/loading path:
#   A1 (OHOS only): libopencsd.so is an AArch64 ELF64 shared object built for
#                   the OHOS arm64 target (not the host Mach-O / x86 ELF);
#   A2 (OHOS only): the ELF SONAME is libopencsd.so.1 (ABI compatibility
#                   guarantee for consumers);
#   A3 (all):       the packaged libopencsd.so loads via dlopen() and
#                   ocsd_get_version() returns 0x010505 (platform dynamic
#                   loader + toolchain-built artifact integration).
#
# Usage: test_ohos.sh <libdir> <os> <dlopen-binary>
set -u

LIBDIR="$1"
OS_NAME="$2"
DLOPEN_BIN="$3"
LIB_FILE="$LIBDIR/libopencsd.so"
CAPI_FILE="$LIBDIR/libopencsd_c_api.so"

if [ ! -f "$LIB_FILE" ]; then
    echo "FAIL: packaged lib not found: $LIB_FILE"
    exit 1
fi

# resolve readelf: llvm-readelf (OHOS SDK) -> readelf
READELF="$(command -v llvm-readelf 2>/dev/null || command -v readelf 2>/dev/null)"
[ -z "$READELF" ] && READELF=""

fails=0

if [ "$OS_NAME" = "OHOS" ]; then
    if [ -z "$READELF" ]; then
        echo "FAIL: no readelf/llvm-readelf available for ELF checks"
        fails=$((fails + 1))
    else
        # A1: AArch64 ELF64 shared object
        if "$READELF" -h "$LIB_FILE" 2>/dev/null | grep -q "Machine:.*AArch64" \
           && "$READELF" -h "$LIB_FILE" 2>/dev/null | grep -q "ELF64"; then
            echo "PASS: A1 $LIB_FILE is AArch64 ELF64"
        else
            echo "FAIL: A1 $LIB_FILE is not AArch64 ELF64"
            "$READELF" -h "$LIB_FILE" 2>/dev/null | head -8
            fails=$((fails + 1))
        fi

        # A2: SONAME == libopencsd.so.1
        if "$READELF" -d "$LIB_FILE" 2>/dev/null | grep -q "SONAME.*libopencsd.so.1"; then
            echo "PASS: A2 SONAME is libopencsd.so.1"
        else
            echo "FAIL: A2 SONAME not libopencsd.so.1"
            "$READELF" -d "$LIB_FILE" 2>/dev/null | grep -i soname || true
            fails=$((fails + 1))
        fi
    fi
else
    echo "SKIP: A1/A2 ELF checks (os=$OS_NAME)"
fi

# A3: dlopen + version check. The C API (ocsd_get_version) lives in
# libopencsd_c_api.so; the dlopen binary pre-loads libopencsd.so.1 by path
# and then loads the C-API lib, verifying dependency resolution + symbol
# binding by the platform dynamic loader.
if [ ! -f "$CAPI_FILE" ]; then
    echo "FAIL: packaged C-API lib not found: $CAPI_FILE"
    fails=$((fails + 1))
elif [ ! -f "$LIBDIR/libopencsd.so.1" ]; then
    echo "FAIL: packaged core lib not found: $LIBDIR/libopencsd.so.1"
    fails=$((fails + 1))
elif [ -x "$DLOPEN_BIN" ]; then
    if "$DLOPEN_BIN" "$LIBDIR/libopencsd.so.1" "$CAPI_FILE" >/dev/null 2>&1; then
        echo "PASS: A3 dlopen chain + ocsd_get_version=0x010505"
    else
        echo "FAIL: A3 dlopen/version check failed"
        "$DLOPEN_BIN" "$LIBDIR/libopencsd.so.1" "$CAPI_FILE" || true
        fails=$((fails + 1))
    fi
else
    echo "FAIL: dlopen binary missing: $DLOPEN_BIN"
    fails=$((fails + 1))
fi

if [ "$fails" -gt 0 ]; then
    echo "FAIL: test_ohos.sh $fails assertion(s) failed"
    exit 1
fi
echo "PASS: test_ohos.sh all checks passed"
exit 0
