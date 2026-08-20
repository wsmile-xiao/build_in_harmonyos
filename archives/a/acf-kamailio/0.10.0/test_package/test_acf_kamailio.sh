#!/bin/sh
# test_acf_kamailio.sh — L1 test for acf-kamailio 0.10.0
# Verifies the packaged pure-Lua ACF Kamailio module:
#   1. Required files exist (controller, model, menu, roles)
#   2. View templates exist (listfiles, listusers, searchdatabase, edit, status)
#   3. Lua sources are syntactically valid (luac -p)
#   4. Package layout matches ACF convention (share/acf/app/kamailio/)
#   5. Controller/model reference the acf-db dependency
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-kamailio package root.
# Priority 1: ACF_KAMAILIO_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for kamailio-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
KAMAILIO_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_KAMAILIO_PKG_ROOT:-}" ] && [ -d "${ACF_KAMAILIO_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_KAMAILIO_PKG_ROOT}"
    # Normalized layout (usr/ stripped): share/acf/app/kamailio/
    KAMAILIO_DIR="${PKG_ROOT}/share/acf/app/kamailio"
    # Fallback: un-normalized layout (usr/ kept)
    if [ ! -d "$KAMAILIO_DIR" ]; then
        KAMAILIO_DIR="${PKG_ROOT}/usr/share/acf/app/kamailio"
    fi
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for kamailio-controller.lua
if [ -z "$KAMAILIO_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        # Try normalized layout first (share/acf/app/kamailio/)
        FOUND=$(find "$CONAN_HOME/p" -path "*/share/acf/app/kamailio/kamailio-controller.lua" 2>/dev/null | head -1)
        if [ -z "$FOUND" ]; then
            # Fallback: un-normalized layout (usr/share/acf/app/kamailio/)
            FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/kamailio/kamailio-controller.lua" 2>/dev/null | head -1)
        fi
        if [ -n "$FOUND" ]; then
            KAMAILIO_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/share/acf/app/kamailio/kamailio-controller.lua$||; s|/usr/share/acf/app/kamailio/kamailio-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$KAMAILIO_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/kamailio-controller.lua" ]; then
        KAMAILIO_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-kamailio L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  kamailio dir: ${KAMAILIO_DIR:-<not found>}"

# Required files per ACF module convention (app/kamailio/)
REQUIRED_FILES="kamailio-controller.lua kamailio-model.lua kamailio.menu kamailio.roles"
for f in $REQUIRED_FILES; do
    if [ -n "$KAMAILIO_DIR" ] && [ -f "$KAMAILIO_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# View template files (listfiles/listusers/searchdatabase are real files;
# edit/status are materialized from acf-core's filedetails/status templates)
VIEW_FILES="kamailio-listfiles-html.lsp kamailio-listusers-html.lsp kamailio-searchdatabase-html.lsp kamailio-edit-html.lsp kamailio-status-html.lsp"
for f in $VIEW_FILES; do
    if [ -n "$KAMAILIO_DIR" ] && [ -e "$KAMAILIO_DIR/$f" ]; then
        if [ -L "$KAMAILIO_DIR/$f" ]; then
            ok "symlink exists: $f -> $(readlink "$KAMAILIO_DIR/$f" 2>/dev/null || echo '?')"
        else
            ok "file exists: $f"
        fi
    else
        no "file missing: $f"
    fi
done

# Lua syntax validation (luac -p) — if luac available
# Only check regular files (not symlinks, which may point to acf-core app)
if command -v luac >/dev/null 2>&1; then
    for f in kamailio-controller.lua kamailio-model.lua; do
        if [ -n "$KAMAILIO_DIR" ] && [ -f "$KAMAILIO_DIR/$f" ]; then
            if luac -p "$KAMAILIO_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: controller must reference dbcontrollerfunctions (dependency on acf-db)
if [ -n "$KAMAILIO_DIR" ] && [ -f "$KAMAILIO_DIR/kamailio-controller.lua" ]; then
    if grep -q "dbcontrollerfunctions" "$KAMAILIO_DIR/kamailio-controller.lua" 2>/dev/null; then
        ok "controller references dbcontrollerfunctions (acf-db dependency)"
    else
        no "controller missing dbcontrollerfunctions reference"
    fi
fi

# Content sanity: model must reference dbmodelfunctions (dependency on acf-db)
if [ -n "$KAMAILIO_DIR" ] && [ -f "$KAMAILIO_DIR/kamailio-model.lua" ]; then
    if grep -q "dbmodelfunctions" "$KAMAILIO_DIR/kamailio-model.lua" 2>/dev/null; then
        ok "model references dbmodelfunctions (acf-db dependency)"
    else
        no "model missing dbmodelfunctions reference"
    fi
fi

# Content sanity: model must reference kamctlrc (Kamailio config)
if [ -n "$KAMAILIO_DIR" ] && [ -f "$KAMAILIO_DIR/kamailio-model.lua" ]; then
    if grep -q "kamctlrc" "$KAMAILIO_DIR/kamailio-model.lua" 2>/dev/null; then
        ok "model references /etc/kamailio/kamctlrc (Kamailio config)"
    else
        no "model missing Kamailio config reference"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
