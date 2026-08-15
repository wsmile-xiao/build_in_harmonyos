#!/bin/sh
# test_acf_apk_tools.sh — L1 test for acf-apk-tools 0.11.0
# Verifies the packaged pure-Lua ACF apk module:
#   1. Required files exist (controller, model, menu, roles, views)
#   2. Files are non-empty and real ACF content (not placeholders)
#   3. Package layout matches ACF convention (share/acf/app/apk-tools/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-apk-tools package root.
# Priority 1: ACF_APK_TOOLS_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for apk-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
PKG_ROOT=""
APK_DIR=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_APK_TOOLS_PKG_ROOT:-}" ] && [ -d "${ACF_APK_TOOLS_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_APK_TOOLS_PKG_ROOT}"
    APK_DIR="${PKG_ROOT}/usr/share/acf/app/apk-tools"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for apk-controller.lua
#    Use $CONAN_HOME if set (inherited from conan), else default to ~/.conan2
if [ -z "$APK_DIR" ]; then
    CONAN_CACHE="${CONAN_HOME:-${HOME}/.conan2}"
    if [ -d "$CONAN_CACHE" ]; then
        FOUND=$(find "$CONAN_CACHE/p" -path "*/usr/share/acf/app/apk-tools/apk-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            APK_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/apk-tools/apk-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$APK_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/apk-controller.lua" ]; then
        APK_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-apk-tools L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  apk dir: ${APK_DIR:-<not found>}"

# Required files per ACF module convention (controller/model/menu/roles + views)
REQUIRED_FILES="apk-controller.lua apk-model.lua apk.menu apk.roles"
for f in $REQUIRED_FILES; do
    if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/$f" ]; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# HTML view templates (.lsp)
LSP_FILES="apk-available-html.lsp apk-details-html.lsp apk-expert-html.lsp apk-loaded-html.lsp"
for f in $LSP_FILES; do
    if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/$f" ]; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# Non-empty sanity: every shipped file must be >0 bytes (real content)
for f in apk-controller.lua apk-model.lua apk.menu apk.roles \
         apk-available-html.lsp apk-details-html.lsp apk-expert-html.lsp apk-loaded-html.lsp; do
    if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/$f" ]; then
        if [ -s "$APK_DIR/$f" ]; then
            ok "non-empty: $f"
        else
            no "empty file: $f"
        fi
    fi
done

# Content sanity: controller must define the acf controller pattern (module table)
if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/apk-controller.lua" ]; then
    if grep -Eq "module|controller|return" "$APK_DIR/apk-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

# Content sanity: model must reference apk commands (real apk-tools integration)
if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/apk-model.lua" ]; then
    if grep -Eq "apk|pkg_installed|pkg_available" "$APK_DIR/apk-model.lua" 2>/dev/null; then
        ok "model has apk-tools integration"
    else
        no "model content unexpected"
    fi
fi

# Lua syntax validation (luac -p) — if luac available
if command -v luac >/dev/null 2>&1; then
    for f in apk-controller.lua apk-model.lua; do
        if [ -n "$APK_DIR" ] && [ -f "$APK_DIR/$f" ]; then
            if luac -p "$APK_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
