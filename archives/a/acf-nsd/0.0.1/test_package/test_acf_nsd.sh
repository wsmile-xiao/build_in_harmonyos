#!/bin/sh
# test_acf_nsd.sh — L1 test for acf-nsd 0.0.1
# Verifies the packaged pure-Lua ACF NSD module:
#   1. Required files exist (controller, model, menu, roles)
#   2. Lua sources are syntactically valid (luac -p)
#   3. Package layout matches ACF convention (share/acf/app/nsd/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-nsd package root.
# Priority 1: ACF_NSD_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for nsd-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
NSD_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_NSD_PKG_ROOT:-}" ] && [ -d "${ACF_NSD_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_NSD_PKG_ROOT}"
    NSD_DIR="${PKG_ROOT}/usr/share/acf/app/nsd"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for nsd-controller.lua
if [ -z "$NSD_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/nsd/nsd-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            NSD_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/nsd/nsd-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$NSD_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/nsd-controller.lua" ]; then
        NSD_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-nsd L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  nsd dir: ${NSD_DIR:-<not found>}"

# Required files per ACF module convention
REQUIRED_FILES="nsd-controller.lua nsd-model.lua nsd.menu nsd.roles"
for f in $REQUIRED_FILES; do
    if [ -n "$NSD_DIR" ] && [ -f "$NSD_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# Lua syntax validation (luac -p) — if luac available
if command -v luac >/dev/null 2>&1; then
    for f in nsd-controller.lua nsd-model.lua; do
        if [ -n "$NSD_DIR" ] && [ -f "$NSD_DIR/$f" ]; then
            if luac -p "$NSD_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: controller must define a Lua table (acf controller pattern)
if [ -n "$NSD_DIR" ] && [ -f "$NSD_DIR/nsd-controller.lua" ]; then
    # Use grep -E for alternation; some lightweight greps don't support \|
    if grep -Eq "module|controller|function|return" "$NSD_DIR/nsd-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
