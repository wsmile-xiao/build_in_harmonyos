#!/bin/sh
# coreutils for HarmonyOS — install.sh
# curl -fsSL <url>/install-coreutils.sh | sh -s -- <version>
#
# tar.gz is flat structure (bin/ share/ lib/ at top level)

VER="${1:-9.10}"
[ -z "$VER" ] && { echo "Usage: sh install-coreutils.sh <version>"; exit 1; }

TMP="$HOME/tmp/install-coreutils-$$"
DST="$HOME/usr/local"
URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/coreutils/coreutils-${VER}-ohos-aarch64.tar.gz"

mkdir -p "$TMP" "$DST" || exit 1

# 1. Download
curl -fSL -o "$TMP/coreutils.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }

# 2. Extract + Install (flat structure)
tar xzf "$TMP/coreutils.tar.gz" -C "$TMP"
rm -f "$TMP/coreutils.tar.gz"
cp -r "$TMP"/* "$DST/"

# 3. Cleanup
rm -rf "$TMP"

# 4. Permissions + PATH
chmod +x "$DST/bin/"* 2>/dev/null || true
grep -q "usr/local/bin" "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/usr/local/bin:$PATH"' >> "$HOME/.zshrc"

# 5. 预触发安全弹窗（HarmonyOS 首次执行二进制需确认）
for bin in "$DST/bin/"*; do [ -f "$bin" ] && "$bin" --version >/dev/null 2>&1 || true; done

echo "=== coreutils $VER installed ==="
