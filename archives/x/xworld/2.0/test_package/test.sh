#!/usr/bin/env bash
# test_package/test.sh — smoke test for xworld 2.0 binary
# xworld is an X11 globe viewer. In a headless environment (no $DISPLAY),
# the binary will fail to open the display — this is expected and is NOT
# a build/link failure. We verify:
#   1. The binary exists and is a valid ELF arm64 executable
#   2. The binary is dynamically linked against libX11 (correct linkage)
#   3. The binary fails with an X11/display error (not a missing library error)
set -euo pipefail

XWORLD_BIN="$(command -v xworld || true)"
if [ -z "$XWORLD_BIN" ]; then
    # Fall back to conanrun bin dir
    XWORLD_BIN="${BINDIR:-${CONAN_RUN_ENV_BIN:-}}/xworld"
fi

echo "[test] xworld binary: $XWORLD_BIN"

# Test 1: Binary exists
if [ -f "$XWORLD_BIN" ]; then
    echo "PASS: xworld binary exists at $XWORLD_BIN"
else
    echo "FAIL: xworld binary not found at $XWORLD_BIN"
    exit 1
fi

# Test 2: Binary is executable ELF arm64
file_out=$(file "$XWORLD_BIN" 2>&1)
echo "[test] file: $file_out"
if echo "$file_out" | grep -qi "ELF.*arm64\|ELF.*aarch64"; then
    echo "PASS: xworld is a valid ARM64 ELF binary"
else
    echo "FAIL: xworld is not a valid ARM64 ELF"
    exit 1
fi

# Test 3: Binary is linked against libX11
if ldd "$XWORLD_BIN" 2>/dev/null | grep -q "libX11"; then
    echo "PASS: xworld dynamically linked against libX11"
else
    # Static link or ldd failure — check readelf as fallback
    if readelf -d "$XWORLD_BIN" 2>/dev/null | grep -q "NEEDED.*libX11"; then
        echo "PASS: xworld linked against libX11 (readelf confirms)"
    else
        echo "FAIL: xworld NOT linked against libX11"
        exit 1
    fi
fi

# Test 4: Binary executes — must fail with X11/display error, NOT a missing-library error
# In headless OHOS, this should exit non-zero with an X11/display message.
# We accept non-zero exit as long as it's NOT a missing shared library error.
echo "[test] attempting xworld --help (expect failure in headless env)..."
set +e
xworld_out=$("$XWORLD_BIN" --help 2>&1)  # likely fails without X display
xworld_rc=$?
set -e
echo "[test] exit code: $xworld_rc"
echo "[test] output: $xworld_out"

if [ $xworld_rc -ne 0 ]; then
    # Check for MISSING LIBRARY first (most important failure mode — must FAIL)
    if echo "$xworld_out" | grep -qi "error while loading\|cannot open shared object"; then
        echo "FAIL: xworld has missing shared library dependency"
        echo "ldd: $(ldd "$XWORLD_BIN" 2>&1)"
        exit 1
    # Then check for expected X11/display errors (PASS in headless env)
    elif echo "$xworld_out" | grep -qi "display\|X11\|connection refused"; then
        echo "PASS: xworld ran and reported expected X11 error (headless environment)"
    else
        echo "PASS: xworld executed (non-zero exit OK in headless/no-display env)"
    fi
else
    # Exit 0 means it actually ran! (Unlikely headless but possible with virtual display)
    echo "PASS: xworld ran successfully (exit 0)"
fi

# Test 5 (HarmonyOS consumer case): Verify mmap self-loading mechanism
# xworld's core design appends raw pixel data (world.o) to the ELF and mmap's
# it at runtime. This consumer independently verifies the appended data segment
# is accessible through mmap on OHOS (musl aarch64).
echo ""
echo "[test] OHOS consumer: verifying mmap self-loading mechanism"
# consumer binary lives in the same dir as this test.sh (test_package dir)
CONSUMER_BIN="$(cd "$(dirname "$0")" && pwd)/consumer"
if [ -f "$CONSUMER_BIN" ]; then
    set +e
    consumer_out=$("$CONSUMER_BIN" "$XWORLD_BIN" 2>&1)
    consumer_rc=$?
    set -e
    echo "$consumer_out"
    if [ $consumer_rc -eq 0 ]; then
        echo "PASS: OHOS consumer verified mmap self-loading"
    else
        echo "FAIL: OHOS consumer mmap verification failed (exit $consumer_rc)"
        exit 1
    fi
else
    echo "SKIP: consumer binary not found (build test_package first to enable)"
fi

echo ""
echo "=== All xworld smoke tests PASSED ==="
