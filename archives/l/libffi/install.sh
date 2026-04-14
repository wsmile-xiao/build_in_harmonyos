#!/bin/sh
# libffi for HarmonyOS — install.sh
# Usage: sh install.sh <version> [prefix]

VER="${1:-}"
[ -z "$VER" ] && { echo "Usage: sh install.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-libffi-$$"
DST="${2:-$HOME/usr/local}"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/libffi/libffi-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. 下载
curl -fSL -o "$TMP/libffi.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. 解压 + 安装
tar xzf "$TMP/libffi.tar.gz" -C "$TMP"
rm -f "$TMP/libffi.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. 清理
rm -rf "$TMP"

# 4. 权限（纯库，无 bin/，不需要 PATH）
chmod +x "$DST/bin/"* 2>/dev/null || true

# 5. 验证
ls "$DST/lib/libffi.so" "$DST/lib/libffi.a" >/dev/null 2>&1 && echo "libffi OK" || echo "Warning: libffi not found"

echo "=== libffi $VER installed ==="
