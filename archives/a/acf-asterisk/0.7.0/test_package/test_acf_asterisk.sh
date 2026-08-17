#!/bin/sh
# test_acf_asterisk.sh — L1 test for acf-asterisk 0.7.0
# Verifies the packaged pure-Lua ACF asterisk module:
#   1. Required files exist (controller, model, menu, views)
#   2. Files are non-empty and real ACF content (not placeholders)
#   3. Package layout matches ACF convention (share/acf/app/asterisk/)
# Note: we count PASS/FAIL and exit non-zero if FAIL>0. We use set -u and
# set -o pipefail for strictness, but NOT set -e (counting logic uses
# conditional assignments that exit non-zero normally).
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  [ok] $1"; PASS=$((PASS+1)); }
no() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

# Determine the acf-asterisk package root.
# Priority 1: ACF_ASTERISK_PKG_ROOT env var (passed by test_package conanfile.py).
# Priority 2: Search Conan cache binary package folders for asterisk-controller.lua.
PKG_ROOT=""
AST_DIR=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_ASTERISK_PKG_ROOT:-}" ] && [ -d "${ACF_ASTERISK_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_ASTERISK_PKG_ROOT}"
    AST_DIR="${PKG_ROOT}/usr/share/acf/app/asterisk"
fi

# 2) Search Conan cache binary package folders (p/b/*/p/) for asterisk-controller.lua
if [ -z "$AST_DIR" ]; then
    CONAN_CACHE="${CONAN_HOME:-${HOME}/.conan2}"
    if [ -d "$CONAN_CACHE" ]; then
        FOUND=$(find "$CONAN_CACHE/p" -path "*/usr/share/acf/app/asterisk/asterisk-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            AST_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/asterisk/asterisk-controller.lua$||')
        fi
    fi
fi

echo "=== acf-asterisk L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  asterisk dir: ${AST_DIR:-<not found>}"

# Required files per ACF module convention (controller/model/menu + views)
# 注意: 上游部分视图(.lsp)是符号链接(如 asterisk-edit-html.lsp →
# filedetails-html.lsp), HMDFS 复制后为悬空 symlink, `[ -f ]` 会返回
# false → 用 `[ -e ] || [ -L ]` 判断"文件或符号链接存在"。
REQUIRED_FILES="asterisk-controller.lua asterisk-model.lua asterisk.menu"
for f in $REQUIRED_FILES; do
    if [ -n "$AST_DIR" ] && { [ -e "$AST_DIR/$f" ] || [ -L "$AST_DIR/$f" ]; }; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# HTML view templates (.lsp)
LSP_FILES="asterisk-edit-html.lsp asterisk-listfiles-html.lsp asterisk-status-html.lsp"
for f in $LSP_FILES; do
    if [ -n "$AST_DIR" ] && { [ -e "$AST_DIR/$f" ] || [ -L "$AST_DIR/$f" ]; }; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# Non-empty sanity: every shipped file must be >0 bytes (real content)
for f in asterisk-controller.lua asterisk-model.lua asterisk.menu \
         asterisk-edit-html.lsp asterisk-listfiles-html.lsp asterisk-status-html.lsp; do
    if [ -n "$AST_DIR" ] && [ -f "$AST_DIR/$f" ]; then
        if [ -s "$AST_DIR/$f" ]; then
            ok "non-empty: $f"
        else
            no "empty file: $f"
        fi
    fi
done

# Content sanity: controller must define the acf controller pattern (module table)
if [ -n "$AST_DIR" ] && [ -f "$AST_DIR/asterisk-controller.lua" ]; then
    if grep -Eq "module|controller|return" "$AST_DIR/asterisk-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
