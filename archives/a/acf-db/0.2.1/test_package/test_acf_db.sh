#!/bin/sh
# test_acf_db.sh — L1 test for acf-db 0.2.1
# Verifies the packaged pure-Lua ACF db module:
#   1. Required files exist (controller, model, menu, roles, lib helpers)
#   2. Lua sources are syntactically valid (luac -p)
#   3. Package layout matches ACF convention (share/acf/app/db/ + share/acf/lib/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-db package root.
# Priority 1: ACF_DB_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for db-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
DB_DIR=""
LIB_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_DB_PKG_ROOT:-}" ] && [ -d "${ACF_DB_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_DB_PKG_ROOT}"
    DB_DIR="${PKG_ROOT}/usr/share/acf/app/db"
    LIB_DIR="${PKG_ROOT}/usr/share/acf/lib"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for db-controller.lua
if [ -z "$DB_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/db/db-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            DB_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/db/db-controller.lua$||')
            LIB_DIR="${PKG_ROOT}/usr/share/acf/lib"
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$DB_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/db-controller.lua" ]; then
        DB_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
        LIB_DIR="$SCRIPT_DIR/lib"
    fi
fi

echo "=== acf-db L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  db dir: ${DB_DIR:-<not found>}"
echo "  lib dir: ${LIB_DIR:-<not found>}"

# Required files per ACF module convention (app/db/)
REQUIRED_FILES="db-controller.lua db-model.lua db.menu db.roles"
for f in $REQUIRED_FILES; do
    if [ -n "$DB_DIR" ] && [ -f "$DB_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# Required lib/ helper files (share/acf/lib/)
LIB_FILES="dbcontrollerfunctions.lua dbmodelfunctions.lua db-listdatabases-html.lsp"
for f in $LIB_FILES; do
    if [ -n "$LIB_DIR" ] && [ -f "$LIB_DIR/$f" ]; then ok "lib file exists: $f"; else no "lib file missing: $f"; fi
done

# Lua syntax validation (luac -p) — if luac available
if command -v luac >/dev/null 2>&1; then
    for f in db-controller.lua db-model.lua; do
        if [ -n "$DB_DIR" ] && [ -f "$DB_DIR/$f" ]; then
            if luac -p "$DB_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: controller must define a Lua table (acf controller pattern)
if [ -n "$DB_DIR" ] && [ -f "$DB_DIR/db-controller.lua" ]; then
    # Use grep -E for alternation; some lightweight greps don't support \|
    if grep -Eq "module|controller|function|return" "$DB_DIR/db-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
