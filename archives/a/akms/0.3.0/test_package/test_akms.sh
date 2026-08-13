#!/bin/sh
# test_akms.sh — L1 test for akms 0.3.0
# Verifies the packaged akms shell tool:
#   1. bin/akms exists and is executable
#   2. akms --version reports 0.3.0
#   3. akms --help exits 0
#   4. helper scripts (akms-build, akms-runas) are installed
# set -e is intentionally omitted: the PASS/FAIL counting logic relies on
# non-zero exits from failed assertions to continue and summarize.
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Locate the akms package root.
# Priority 1: AKMS_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search the Conan cache for the packaged akms script.
PKG_ROOT=""
if [ -n "${AKMS_PKG_ROOT:-}" ] && [ -f "${AKMS_PKG_ROOT}/bin/akms" ]; then
    PKG_ROOT="${AKMS_PKG_ROOT}"
fi
if [ -z "$PKG_ROOT" ]; then
    FOUND=$(find "$HOME/.conan2/p" -path "*/bin/akms" -type f 2>/dev/null | head -1)
    if [ -n "$FOUND" ]; then
        PKG_ROOT=$(echo "$FOUND" | sed 's|/bin/akms$||')
    fi
fi

echo "=== akms L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"

if [ -z "$PKG_ROOT" ] || [ ! -f "$PKG_ROOT/bin/akms" ]; then
    no "bin/akms not found"
    echo ""
    echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
    exit 1
fi
ok "bin/akms exists"

# Executable bit
if [ -x "$PKG_ROOT/bin/akms" ]; then
    ok "bin/akms is executable"
else
    no "bin/akms not executable"
fi

# 1) --version
VERSION_OUT=$("$PKG_ROOT/bin/akms" --version 2>/dev/null)
VERSION_LINE=$(echo "$VERSION_OUT" | head -1)
if echo "$VERSION_LINE" | grep -q "0.3.0"; then
    ok "version reports 0.3.0: $VERSION_LINE"
else
    no "version mismatch: $VERSION_LINE"
fi

# 2) --help
if "$PKG_ROOT/bin/akms" --help >/dev/null 2>&1; then
    ok "--help exits 0"
else
    no "--help failed"
fi

# 3) helper scripts installed
for h in akms-build akms-runas; do
    if [ -f "$PKG_ROOT/libexec/akms/$h" ]; then
        ok "helper installed: $h"
    else
        no "helper missing: $h"
    fi
done

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
