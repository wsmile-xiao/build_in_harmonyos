#!/bin/bash
# Test script for sxmo-st 0.8.4.1
#
# Verifies:
# 1. st binary exists and is executable.
# 2. ELF properties are correct (GNU_RELRO, no exec stack).
# 3. OHOS consumer test (X11/Xft/fontconfig linkage) compiles and runs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="${1:-/tmp/sxmo-st-test-package}"
ST_BIN="${PACKAGE_DIR}/bin/st"
CONSUMER_SRC="${SCRIPT_DIR}/ohos_x11_consumer.c"
CONSUMER_BIN="/data/storage/el2/base/cache/sxmo-st-consumer-test"

echo "=== sxmo-st Test Script ==="
echo "Package dir: ${PACKAGE_DIR}"

# --- Test 1: Binary exists ---
echo "[Test 1] Checking st binary exists..."
if [ ! -f "${ST_BIN}" ]; then
    echo "[fail] st binary not found at ${ST_BIN}"
    exit 1
fi
echo "        [ok] st binary found"

# --- Test 2: Binary is executable ---
echo "[Test 2] Checking st is executable..."
if [ ! -x "${ST_BIN}" ]; then
    echo "[fail] st binary not executable"
    exit 1
fi
echo "        [ok] st binary is executable"

# --- Test 3: ELF verification ---
echo "[Test 3] Checking ELF properties..."
READELF=$(command -v llvm-readelf || command -v readelf || true)
if [ -n "${READELF}" ]; then
    if ${READELF} -l "${ST_BIN}" 2>/dev/null | grep -q "GNU_RELRO"; then
        echo "        [ok] GNU_RELRO present"
    else
        echo "        [warn] GNU_RELRO not found"
    fi

    STACK_LINE=$(${READELF} -l "${ST_BIN}" 2>/dev/null | grep "GNU_STACK" || true)
    if echo "${STACK_LINE}" | grep -q "RWE"; then
        echo "[fail] Executable stack (RWE)"
        exit 1
    else
        echo "        [ok] No executable stack"
    fi

    if ${READELF} -d "${ST_BIN}" 2>/dev/null | grep -q "BIND_NOW"; then
        echo "        [ok] BIND_NOW present"
    else
        echo "        [warn] BIND_NOW not found"
    fi
else
    echo "        [warn] No readelf available, ELF checks skipped"
fi

# --- Test 4: OHOS consumer test (X11/Xft/fontconfig) ---
echo "[Test 4] OHOS consumer test (X11/Xft/fontconfig linkage)..."
CC=$(command -v clang || command -v gcc || true)
if [ -n "${CC}" ] && [ -f "${CONSUMER_SRC}" ]; then
    CONSUMER_CFLAGS=$(pkg-config --cflags x11 xft fontconfig freetype2 2>/dev/null || true)
    CONSUMER_LIBS=$(pkg-config --libs x11 xft fontconfig freetype2 2>/dev/null || true)

    if ${CC} -o "${CONSUMER_BIN}" "${CONSUMER_SRC}" ${CONSUMER_CFLAGS} ${CONSUMER_LIBS} 2>/dev/null; then
        echo "        [ok] Consumer test compiled"

        if "${CONSUMER_BIN}" 2>&1; then
            echo "        [ok] OHOS consumer test passed"
        else
            echo "[fail] OHOS consumer test failed"
            exit 1
        fi

        rm -f "${CONSUMER_BIN}"
    else
        echo "[fail] Could not compile consumer test"
        exit 1
    fi
else
    echo "        [warn] No C compiler or consumer source, consumer test skipped"
fi

echo "=== ALL TESTS PASSED ==="
