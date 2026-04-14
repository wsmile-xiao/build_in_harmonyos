#!/bin/sh
# openssl for HarmonyOS — install.sh
# Usage: sh install.sh <version> [prefix]

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-openssl-$$"
DST="${2:-$HOME/usr/local}"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/openssl/openssl-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/openssl.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装
tar xzf "$TMP/openssl.tar.gz" -C "$TMP"
rm -f "$TMP/openssl.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限 + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

# 5. LD_LIBRARY_PATH（openssl 依赖 lib/ 下动态库）
grep -q "$DST/lib" "$HOME/.zshrc" 2>/dev/null || \
    echo "export LD_LIBRARY_PATH=\"$DST/lib:\$LD_LIBRARY_PATH\"" >> "$HOME/.zshrc"

# 6. 预触发安全弹窗
"$DST/bin/openssl" version >/dev/null 2>&1 || true

echo "=== openssl $VER installed ==="
