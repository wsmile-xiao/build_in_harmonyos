#!/bin/sh
# {PKG_NAME} for HarmonyOS — install.sh
# curl -fsSL <url>/install.sh | sh -s -- <version>
#
# tar.gz 为扁平结构 (bin/ share/ 在顶层)，直接 cp 即可。

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-{PKG_NAME}-$$"
DST="$HOME/usr/local"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/{PKG_NAME}/{PKG_NAME}-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/{PKG_NAME}.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装（扁平结构: bin/ share/ lib/ 在顶层）
tar xzf "$TMP/{PKG_NAME}.tar.gz" -C "$TMP"
rm -f "$TMP/{PKG_NAME}.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限 + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

echo "=== {PKG_NAME} $VER installed ==="
"$DST/bin/{PKG_NAME}" --version | head -1
