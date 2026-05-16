#!/bin/sh
# libdvdcss for HarmonyOS — install.sh
# curl -fsSL <url>/install.sh | sh -s -- <version>
#
# tar.gz 为扁平结构 (bin/ lib/ share/ 在顶层)，直接 cp 即可。

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-libdvdcss-$$"
DST="$HOME/usr/local"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/libdvdcss/libdvdcss-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/libdvdcss.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装（扁平结构: bin/ lib/ share/ 在顶层）
tar xzf "$TMP/libdvdcss.tar.gz" -C "$TMP"
rm -f "$TMP/libdvdcss.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限 + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q 'usr/local/bin' "$HOME/.zshrc" 2>/dev/null || \\
    echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

# 5. 预触发安全弹窗（HarmonyOS 首次执行二进制需确认）
"$DST/bin/libdvdcss" --version >/dev/null 2>&1 || true

echo "=== libdvdcss $VER installed ==="
