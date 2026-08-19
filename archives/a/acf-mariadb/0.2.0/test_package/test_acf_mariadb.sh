#!/bin/sh
# test_acf_mariadb.sh — L1 test for acf-mariadb 0.2.0
# Verifies the packaged pure-Lua ACF mariadb module:
#   1. Required files exist (controller, model, menu, roles, views)
#   2. Lua sources are syntactically valid (luac -p)
#   3. Package layout matches ACF convention (share/acf/app/mysql/)
#   4. Symlinks for shared views exist (expert, logfile, status)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  ✅ $1"; PASS=$((PASS+1)); }
no() { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

# Determine the acf-mariadb package root.
# Priority 1: ACF_MARIADB_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for mysql-controller.lua.
# Priority 3: Source layout fallback (if running directly on the extracted tarball).
MYSQL_DIR=""
PKG_ROOT=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_MARIADB_PKG_ROOT:-}" ] && [ -d "${ACF_MARIADB_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_MARIADB_PKG_ROOT}"
    # Normalized layout (usr/ stripped): share/acf/app/mysql/
    MYSQL_DIR="${PKG_ROOT}/share/acf/app/mysql"
    # Fallback: un-normalized layout (usr/ kept)
    if [ ! -d "$MYSQL_DIR" ]; then
        MYSQL_DIR="${PKG_ROOT}/usr/share/acf/app/mysql"
    fi
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for mysql-controller.lua
if [ -z "$MYSQL_DIR" ]; then
    CONAN_HOME="${HOME}/.conan2"
    if [ -d "$CONAN_HOME" ]; then
        # Try normalized layout first (share/acf/app/mysql/)
        FOUND=$(find "$CONAN_HOME/p" -path "*/share/acf/app/mysql/mysql-controller.lua" 2>/dev/null | head -1)
        if [ -z "$FOUND" ]; then
            # Fallback: un-normalized layout (usr/share/acf/app/mysql/)
            FOUND=$(find "$CONAN_HOME/p" -path "*/usr/share/acf/app/mysql/mysql-controller.lua" 2>/dev/null | head -1)
        fi
        if [ -n "$FOUND" ]; then
            MYSQL_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/share/acf/app/mysql/mysql-controller.lua$||; s|/usr/share/acf/app/mysql/mysql-controller.lua$||')
        fi
    fi
fi

# 3) Source layout fallback (test_package directory or extracted tarball)
if [ -z "$MYSQL_DIR" ]; then
    SCRIPT_DIR=$(dirname "$0")
    if [ -f "$SCRIPT_DIR/mysql-controller.lua" ]; then
        MYSQL_DIR="$SCRIPT_DIR"
        PKG_ROOT="$SCRIPT_DIR"
    fi
fi

echo "=== acf-mariadb L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  mysql dir: ${MYSQL_DIR:-<not found>}"

# Required files per ACF module convention (app/mysql/)
REQUIRED_FILES="mysql-controller.lua mysql-model.lua mysql.menu mysql.roles"
for f in $REQUIRED_FILES; do
    if [ -n "$MYSQL_DIR" ] && [ -f "$MYSQL_DIR/$f" ]; then ok "file exists: $f"; else no "file missing: $f"; fi
done

# Required view template files (copied from acf-core's lib/ with mysql-* prefix)
VIEW_FILES="mysql-details-html.lsp mysql-expert-html.lsp mysql-logfile-html.lsp mysql-status-html.lsp"
for f in $VIEW_FILES; do
    if [ -n "$MYSQL_DIR" ] && [ -e "$MYSQL_DIR/$f" ]; then
        if [ -L "$MYSQL_DIR/$f" ]; then
            ok "symlink exists: $f -> $(readlink "$MYSQL_DIR/$f" 2>/dev/null || echo '?')"
        else
            ok "file exists: $f"
        fi
    else
        no "file missing: $f"
    fi
done

# Lua syntax validation (luac -p) — if luac available
# Only check regular files (not symlinks, which may point to acf-core lib)
if command -v luac >/dev/null 2>&1; then
    for f in mysql-controller.lua mysql-model.lua; do
        if [ -n "$MYSQL_DIR" ] && [ -f "$MYSQL_DIR/$f" ]; then
            if luac -p "$MYSQL_DIR/$f" 2>/dev/null; then ok "lua syntax OK: $f"; else no "lua syntax FAIL: $f"; fi
        fi
    done
else
    echo "  ⚠️  luac not available; skipping Lua syntax check"
fi

# Content sanity: controller must reference dbcontrollerfunctions (dependency on acf-db)
if [ -n "$MYSQL_DIR" ] && [ -f "$MYSQL_DIR/mysql-controller.lua" ]; then
    if grep -q "dbcontrollerfunctions" "$MYSQL_DIR/mysql-controller.lua" 2>/dev/null; then
        ok "controller references dbcontrollerfunctions (acf-db dependency)"
    else
        no "controller missing dbcontrollerfunctions reference"
    fi
fi

# Content sanity: model must reference dbmodelfunctions (dependency on acf-db)
if [ -n "$MYSQL_DIR" ] && [ -f "$MYSQL_DIR/mysql-model.lua" ]; then
    if grep -q "dbmodelfunctions" "$MYSQL_DIR/mysql-model.lua" 2>/dev/null; then
        ok "model references dbmodelfunctions (acf-db dependency)"
    else
        no "model missing dbmodelfunctions reference"
    fi
fi

# Content sanity: model must reference conffile for mariadb
if [ -n "$MYSQL_DIR" ] && [ -f "$MYSQL_DIR/mysql-model.lua" ]; then
    if grep -q "my.cnf" "$MYSQL_DIR/mysql-model.lua" 2>/dev/null; then
        ok "model references /etc/mysql/my.cnf (MariaDB config)"
    else
        no "model missing MariaDB config reference"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
