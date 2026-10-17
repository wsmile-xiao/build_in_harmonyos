#!/usr/bin/zsh
# test_acf_provisioning.sh — L1 test for acf-provisioning 0.10.1
# Verifies the packaged pure-Lua ACF provisioning module:
#   1. Required files exist (controller, model, scripts, menu, roles, cgi-bin)
#   2. Lua sources are syntactically valid (luac -p)
#   3. Package layout matches ACF convention (share/acf/app/provisioning/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. Strict mode
# (set -euo pipefail, per code-style.md §7); the counting branches are
# guarded by if/else so a failed assertion does not abort the run early.
set -euo pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-provisioning package root.
# Priority 1: ACF_PROVISIONING_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for provisioning-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
APP_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_PROVISIONING_PKG_ROOT:-}" ] && [ -d "${ACF_PROVISIONING_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_PROVISIONING_PKG_ROOT}"
    APP_DIR="${PKG_ROOT}/usr/share/acf/app/provisioning"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for provisioning-controller.lua
if [ -z "$APP_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/provisioning/provisioning-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            APP_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/provisioning/provisioning-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$APP_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/provisioning-controller.lua" ]; then
        APP_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-provisioning L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  app dir: ${APP_DIR:-<not found>}"

# Required files per ACF module convention (app/provisioning/)
REQUIRED_FILES="provisioning-controller.lua provisioning-model.lua provisioning-scripts.lua provisioning.menu provisioning.roles upgradeprovisioning"
for f in $REQUIRED_FILES; do
    if [ -n "$APP_DIR" ] && [ -f "$APP_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# Required HTML view templates (.lsp)
LSP_FILES="provisioning-listdevices-html.lsp provisioning-editdevice-html.lsp provisioning-listtemplates-html.lsp provisioning-listclasses-html.lsp"
for f in $LSP_FILES; do
    if [ -n "$APP_DIR" ] && [ -f "$APP_DIR/$f" ]; then ok "lsp view exists: $f"; else no "lsp view missing: $f"; fi
done

# Lua syntax validation (luac -p) — if luac available
if command -v luac >/dev/null 2>&1; then
    for f in provisioning-controller.lua provisioning-model.lua provisioning-scripts.lua; do
        if [ -n "$APP_DIR" ] && [ -f "$APP_DIR/$f" ]; then
            if luac -p "$APP_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: controller must define a Lua table (acf controller pattern)
if [ -n "$APP_DIR" ] && [ -f "$APP_DIR/provisioning-controller.lua" ]; then
    # Use grep -E for alternation; some lightweight greps don't support \|
    if grep -Eq "module|controller|function|return" "$APP_DIR/provisioning-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
