#!/bin/sh
# readline for HarmonyOS — install.sh
# Usage: sh install.sh <version> [prefix]

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-readline-$$"
DST="${2:-$HOME/usr/local}"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/readline/readline-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/readline.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装
tar xzf "$TMP/readline.tar.gz" -C "$TMP"
rm -f "$TMP/readline.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限（纯库，无 bin/）
chmod +x "$DST/bin/"* 2>/dev/null || true

# 5. 验证库文件
ls "$DST/lib/libreadline.so" "$DST/lib/libhistory.so" >/dev/null 2>&1 && echo "readline OK" || echo "Warning: readline libs not found"

echo "=== readline $VER installed ==="
