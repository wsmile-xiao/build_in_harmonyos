#!/bin/bash
# Verify the packaged ACF awall module files are installed.
# Usage: test_awall.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/awall"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

# Core module files (from upstream Makefile APP_DIST: awall*)
# awall-editpolicy-html.lsp / awall-status-html.lsp / awall-viewpolicy-html.lsp
# 是指向 acf-core 共享模板(filedetails-html.lsp/status-html.lsp)的悬空符号链接,
# 目标由 ACF 框架宿主运行时提供 → 用 -L 检查链接本身存在
# (与上游 cp -a 复制链接本身的语义一致),不解析链接目标。
REQUIRED=(
    awall-controller.lua
    awall-model.lua
    awall.roles
    awall.menu
    awall-editpolicy-html.lsp
    awall-listpolicies-html.lsp
    awall-status-html.lsp
    awall-viewpolicy-html.lsp
)

for name in "${REQUIRED[@]}"; do
    f="$APPDIR/$name"
    if [ ! -e "$f" ] && [ ! -L "$f" ]; then
        echo "ERROR: required module file missing: $f"
        exit 1
    fi
    if [ -L "$f" ]; then
        echo "  [ok] $name (symlink -> $(readlink "$f"))"
    else
        echo "  [ok] $name"
    fi
done

echo "=== Results: ${#REQUIRED[@]} passed, 0 failed ==="
exit 0
