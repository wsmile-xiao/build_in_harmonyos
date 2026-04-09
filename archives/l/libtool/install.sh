#!/bin/sh
# ==============================================================================
# [Layer 3] install-template.sh - 软件安装模板（辅助工具）
# ==============================================================================
# 层级: L3(辅助工具)
# 决策点: AI主导（模板需按软件定制 libtool 等占位符）
# 入口: sh scripts/install-template.sh <版本>（需先替换占位符）
# 依赖: curl, tar
# 调用者: 用户（从 release 页面下载后执行）
# ==============================================================================
# libtool for HarmonyOS — install.sh
# curl -fsSL <url>/install.sh | sh -s -- <version>
#
# tar.gz 为扁平结构 (bin/ share/ 在顶层)，直接 cp 即可。

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-libtool-$$"
DST="$HOME/usr/local"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/libtool/libtool-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/libtool.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装（扁平结构: bin/ share/ lib/ 在顶层）
tar xzf "$TMP/libtool.tar.gz" -C "$TMP"
rm -f "$TMP/libtool.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限 + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

echo "=== libtool $VER installed ==="
"$DST/bin/libtool" --version | head -1
