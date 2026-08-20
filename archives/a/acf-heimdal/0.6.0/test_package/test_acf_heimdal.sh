#!/bin/sh
# test_acf_heimdal.sh — L1 test for acf-heimdal 0.6.0
# Verifies the packaged pure-Lua ACF heimdal module:
#   1. Required files exist (controller, model, menu, roles, klist view)
#   2. Shared views are materialized as regular files (expert, status)
#   3. Lua sources are syntactically valid (luac -p)
#   4. Package layout matches ACF convention (share/acf/app/heimdal/)
#   5. Model/view reference their declared dependencies (acf-core, acf-lib-lua5.4)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-heimdal package root.
# Priority 1: ACF_HEIMDAL_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for heimdal-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
HEIMDAL_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_HEIMDAL_PKG_ROOT:-}" ] && [ -d "${ACF_HEIMDAL_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_HEIMDAL_PKG_ROOT}"
    # Normalized layout (usr/ stripped): share/acf/app/heimdal/
    HEIMDAL_DIR="${PKG_ROOT}/share/acf/app/heimdal"
    # Fallback: un-normalized layout (usr/ kept)
    if [ ! -d "$HEIMDAL_DIR" ]; then
        HEIMDAL_DIR="${PKG_ROOT}/usr/share/acf/app/heimdal"
    fi
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for heimdal-controller.lua
if [ -z "$HEIMDAL_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        # Try normalized layout first (share/acf/app/heimdal/)
        FOUND=$(find "$CONAN_HOME/p" -path "*/share/acf/app/heimdal/heimdal-controller.lua" 2>/dev/null | head -1)
        if [ -z "$FOUND" ]; then
            # Fallback: un-normalized layout (usr/share/acf/app/heimdal/)
            FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/heimdal/heimdal-controller.lua" 2>/dev/null | head -1)
        fi
        if [ -n "$FOUND" ]; then
            HEIMDAL_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/share/acf/app/heimdal/heimdal-controller.lua$||; s|/usr/share/acf/app/heimdal/heimdal-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$HEIMDAL_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/heimdal-controller.lua" ]; then
        HEIMDAL_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-heimdal L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  heimdal dir: ${HEIMDAL_DIR:-<not found>}"

# Required files per ACF module convention (app/heimdal/)
REQUIRED_FILES="heimdal-controller.lua heimdal-model.lua heimdal.menu heimdal.roles heimdal-klist-html.lsp"
for f in $REQUIRED_FILES; do
    if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# Materialized shared views: must be regular files (NOT dangling symlinks)
VIEW_FILES="heimdal-expert-html.lsp heimdal-status-html.lsp"
for f in $VIEW_FILES; do
    if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/$f" ]; then
        if [ -L "$HEIMDAL_DIR/$f" ]; then
            no "view is dangling symlink (should be materialized): $f"
        else
            ok "materialized view (regular file): $f"
        fi
    else
        no "view missing: $f"
    fi
done

# Lua syntax validation (luac -p) — if luac available
if command -v luac >/dev/null 2>&1; then
    for f in heimdal-controller.lua heimdal-model.lua; do
        if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/$f" ]; then
            if luac -p "$HEIMDAL_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: model must require modelfunctions (acf-core dependency)
if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/heimdal-model.lua" ]; then
    if grep -q "modelfunctions" "$HEIMDAL_DIR/heimdal-model.lua" 2>/dev/null; then
        ok "model requires modelfunctions (acf-core dependency)"
    else
        no "model missing modelfunctions reference"
    fi
fi

# Content sanity: model must require acf.fs (acf-lib-lua5.4 dependency)
if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/heimdal-model.lua" ]; then
    if grep -q "acf.fs" "$HEIMDAL_DIR/heimdal-model.lua" 2>/dev/null; then
        ok "model requires acf.fs (acf-lib-lua5.4 dependency)"
    else
        no "model missing acf.fs reference"
    fi
fi

# Content sanity: model must reference Heimdal config krb5.conf
if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/heimdal-model.lua" ]; then
    if grep -q "krb5.conf" "$HEIMDAL_DIR/heimdal-model.lua" 2>/dev/null; then
        ok "model references /etc/krb5.conf (Heimdal config)"
    else
        no "model missing Heimdal config reference"
    fi
fi

# Content sanity: klist view must require acf.html (acf-lib-lua5.4 dependency)
if [ -n "$HEIMDAL_DIR" ] && [ -f "$HEIMDAL_DIR/heimdal-klist-html.lsp" ]; then
    if grep -q "acf.html" "$HEIMDAL_DIR/heimdal-klist-html.lsp" 2>/dev/null; then
        ok "klist view requires acf.html (acf-lib-lua5.4 dependency)"
    else
        no "klist view missing acf.html reference"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
