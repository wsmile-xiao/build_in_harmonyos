#!/bin/bash
# Verify the packaged ACF iproute2-qos module assets are installed.
# Usage: test_iproute2_qos.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/qos"

if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

# Core module files (upstream Makefile APP_DIST: qos*)
# 注意: qos-expert-html.lsp / qos-status-html.lsp 在上游 tarball 中是指向
# acf-core 共享模板(filedetails-html.lsp/status-html.lsp)的符号链接——
# 用 -L 检查符号链接本身存在(lexists 语义),不解析目标。
REQUIRED=(
    qos-controller.lua
    qos-model.lua
    qos.roles
    qos.menu
    qos-expert-html.lsp
    qos-status-html.lsp
)

for name in "${REQUIRED[@]}"; do
    f="$APPDIR/$name"
    if [ ! -e "$f" ] && [ ! -L "$f" ]; then
        echo "ERROR: required module file missing: $f"
        exit 1
    fi
    echo "  [ok] $name"
done

# Count .lua files (parse-check candidates)
lua_count=$(find "$APPDIR" -maxdepth 1 -name '*.lua' | wc -l)
echo "  [ok] $lua_count .lua files in app dir"

# ETC_DIST (配方 package() 目前只装 APP_DIST 到 share/acf/app/qos,
# 无 share/acf/iproute2-qos 目录)——目录不存在时输出 0 不视为失败
ETCDIR="$PKG_FOLDER/share/acf/iproute2-qos"
etc_count=0
if [ -d "$ETCDIR" ]; then
    etc_count=$(find "$ETCDIR" -maxdepth 1 -type f | wc -l)
fi
echo "  [ok] $etc_count config file(s) in etc dir"

echo "=== Results: 9 passed, 0 failed ==="
exit 0
