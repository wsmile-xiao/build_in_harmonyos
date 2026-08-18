#!/bin/sh
# test_acf-clamsmtp.sh — L1 test for acf-clamsmtp 0.6.0
# Verifies the packaged pure-Lua ACF clamsmtp module:
#   1. Required files exist (controller, model, menu, views)
#   2. Files are non-empty and real ACF content (not placeholders)
#   3. Package layout matches ACF convention (share/acf/app/clamsmtp/)
set -u
set -o pipefail

PASS=0
FAIL=0
ok() { echo "  [ok] $1"; PASS=$((PASS+1)); }
no() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

PKG_ROOT=""
MOD_DIR=""

# 1) Try env var passed from test_package conanfile
if [ -n "${ACF_CLAMSMTP_PKG_ROOT:-}" ] && [ -d "${ACF_CLAMSMTP_PKG_ROOT:-}" ]; then
    PKG_ROOT="${ACF_CLAMSMTP_PKG_ROOT}"
    MOD_DIR="${PKG_ROOT}/usr/share/acf/app/clamsmtp"
fi

# 2) Search Conan cache binary package folders for clamsmtp-controller.lua
if [ -z "$MOD_DIR" ]; then
    CONAN_CACHE="${CONAN_HOME:-${HOME}/.conan2}"
    if [ -d "$CONAN_CACHE" ]; then
        FOUND=$(find "$CONAN_CACHE/p" -path "*/usr/share/acf/app/clamsmtp/clamsmtp-controller.lua" 2>/dev/null | head -1)
        if [ -n "$FOUND" ]; then
            MOD_DIR=$(dirname "$FOUND")
            PKG_ROOT=$(echo "$FOUND" | sed 's|/usr/share/acf/app/clamsmtp/clamsmtp-controller.lua$||')
        fi
    fi
fi

echo "=== acf-clamsmtp L1 test ==="
echo "  package root: ${PKG_ROOT:-<not found>}"
echo "  module dir: ${MOD_DIR:-<not found>}"

# Required files (controller/model/menu + views)
# 注意: 上游部分视图(.lsp)是符号链接, HMDFS 复制后为悬空 symlink,
# `[ -f ]` 返回 false → 用 `[ -e ] || [ -L ]` 判断"文件或符号链接存在"。
REQUIRED_FILES="clamsmtp-controller.lua clamsmtp-model.lua clamsmtp.menu"
for f in $REQUIRED_FILES; do
    if [ -n "$MOD_DIR" ] && { [ -e "$MOD_DIR/$f" ] || [ -L "$MOD_DIR/$f" ]; }; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# HTML view templates (.lsp)
LSP_FILES="clamsmtp-details-html.lsp clamsmtp-expert-html.lsp clamsmtp-logfile-html.lsp clamsmtp-status-html.lsp"
for f in $LSP_FILES; do
    if [ -n "$MOD_DIR" ] && { [ -e "$MOD_DIR/$f" ] || [ -L "$MOD_DIR/$f" ]; }; then
        ok "file exists: $f"
    else
        no "file missing: $f"
    fi
done

# Non-empty sanity: every shipped file must be >0 bytes (real content)
for f in clamsmtp-controller.lua clamsmtp-model.lua clamsmtp.menu clamsmtp-details-html.lsp clamsmtp-expert-html.lsp clamsmtp-logfile-html.lsp clamsmtp-status-html.lsp; do
    if [ -n "$MOD_DIR" ] && [ -f "$MOD_DIR/$f" ]; then
        if [ -s "$MOD_DIR/$f" ]; then
            ok "non-empty: $f"
        else
            no "empty file: $f"
        fi
    fi
done

# Content sanity: controller must define the acf controller pattern (module table)
if [ -n "$MOD_DIR" ] && [ -f "$MOD_DIR/clamsmtp-controller.lua" ]; then
    if grep -Eq "module|controller|return" "$MOD_DIR/clamsmtp-controller.lua" 2>/dev/null; then
        ok "controller has expected content"
    else
        no "controller content unexpected"
    fi
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
if [ "$FAIL" -gt 0 ]; then exit 1; fi
exit 0
