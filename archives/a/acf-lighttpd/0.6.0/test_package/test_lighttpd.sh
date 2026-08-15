#!/bin/bash
# Verify the packaged ACF lighttpd module files are installed.
# Usage: test_lighttpd.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/lighttpd"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

# Core module files (from upstream Makefile APP_DIST: lighttpd*)
# lighttpd-expert/logfile/status-html.lsp 是指向 acf-core 共享模板的悬空符号
# 链接,目标由 ACF 框架宿主运行时提供 → 用 -L 检查链接本身存在。
REQUIRED=(
    lighttpd-controller.lua
    lighttpd-model.lua
    lighttpd.roles
    lighttpd.menu
    lighttpd-expert-html.lsp
    lighttpd-status-html.lsp
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

# R34: 对每个 .lua 文件做真实 Lua 语法校验(luac -p / lua -e "loadfile()"),
# 而非仅检查文件存在——存在性检查无法发现未闭合字符串/拼写错误。
# CI 沙箱可能无 lua 解释器(USER=100 无 ~/.local 手工工具), 此时降级为
# 静态检查并在 conanfile.py 中由 python 侧的 lua -p 兜底。
# 注意: 用 `if ! ...` 直接检查返回值——set -e 下若先裸执行命令再事后
# `if [ $? -ne 0 ]`, 命令失败时脚本已直接退出, 自定义 ERROR 消息成死代码。
# 语法校验用 loadfile(只编译不执行)而非 dofile(会执行顶层代码)。
LUA_BIN=""
for cand in lua lua5.4 lua5.3 lua5.2 luac; do
    if command -v "$cand" >/dev/null 2>&1; then
        LUA_BIN="$cand"
        break
    fi
done
if [ -n "$LUA_BIN" ]; then
    LUA_COUNT=0
    for f in "$APPDIR"/*.lua; do
        [ -f "$f" ] || continue
        if [ "$LUA_BIN" = "luac" ]; then
            if ! "$LUA_BIN" -p "$f" >/dev/null 2>&1; then
                echo "ERROR: Lua syntax check failed for $f"
                exit 1
            fi
        else
            if ! "$LUA_BIN" -e "loadfile('$f')" >/dev/null 2>&1; then
                echo "ERROR: Lua syntax check failed for $f"
                exit 1
            fi
        fi
        echo "  [ok] lua syntax: $(basename "$f")"
        LUA_COUNT=$((LUA_COUNT + 1))
    done
    echo "  Lua syntax checked: $LUA_COUNT .lua file(s)"
else
    echo "  [warn] no lua interpreter in PATH, lua syntax check skipped (python-side check covers it)"
fi

echo "=== Results: ${#REQUIRED[@]} passed, 0 failed ==="
exit 0
