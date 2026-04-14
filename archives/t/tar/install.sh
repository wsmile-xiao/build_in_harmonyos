#!/bin/sh
# tar for HarmonyOS — install.sh
# Usage: sh install.sh <version> [prefix]

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-tar-$$"
DST="${2:-$HOME/usr/local}"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/tar/tar-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/tar.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装
tar xzf "$TMP/tar.tar.gz" -C "$TMP"
rm -f "$TMP/tar.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限 + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

# 5. 预触发安全弹窗
"$DST/bin/tar" --version >/dev/null 2>&1 || true

echo "=== tar $VER installed ==="
