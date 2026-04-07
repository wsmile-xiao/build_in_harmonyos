#!/bin/sh
# HarmonyOS aarch64 预编译软件 — 通用安装脚本 (POSIX sh)
# 用法: curl -fsSL <URL>/install.sh | sh

ARCH="$(uname -m)"
DEST="$HOME/usr/local"
BIN_DIR="$DEST/bin"
PC_DIR="$DEST/lib/pkgconfig"

# ---- 检测包信息 ----
PKG_NAME="${PKG_NAME:-pkg-config}"
PKG_VERSION="${PKG_VERSION:-0.29.2}"
TAR_NAME="${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}.tar.gz"
URL_BASE="${INSTALL_URL:-https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/${PKG_NAME}-${PKG_VERSION}}"

# ---- Step 1: 获取 tarball ----
if [ -f "${TAR_NAME}" ]; then
    TAR_SRC="$(pwd)/${TAR_NAME}"
else
    DL_DIR="${HOME}/tmp"; mkdir -p "$DL_DIR" 2>/dev/null || DL_DIR="."
    for URL in "${URL_BASE}/${TAR_NAME}" "${URL_BASE}.gitee/${TAR_NAME}"; do
        if curl -fSL --connect-timeout 30 --max-time 300 -o "${DL_DIR}/${TAR_NAME}" "$URL" 2>/dev/null; then
            TAR_SRC="${DL_DIR}/${TAR_NAME}"; break
        fi
    done
fi
[ -z "$TAR_SRC" ] && { echo "Error: download failed"; exit 1; }

# ---- Step 2: 解压到 ~/usr/local/（扁平结构）----
mkdir -p "$DEST"
_TMPD="${TMPDIR:-$HOME/tmp}/pkginst-$$"
mkdir -p "$_TMPD"
tar xzf "$TAR_SRC" -C "$_TMPD"
rm -f "$TAR_SRC"
# 将内层目录内容提升到 DEST（兼容 toybox tar 无 --strip-components）
for _d in "$_TMPD"/*/; do
    [ -d "$_d" ] || continue
    cp -a "$_d"* "$DEST/" 2>/dev/null || true
done
rm -rf "$_TMPD"

# ---- Step 3: 确保可执行权限 ----
chmod +x "$DEST"/bin/* 2>/dev/null || true

# ---- Step 4: 环境变量（仅 PATH 缺失时写入 .zshrc）----
_NEED_RC=0
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) _NEED_RC=1;; esac

if [ "$_NEED_RC" = "1" ] && [ -n "$HOME" ]; then
    [ ! -f "$HOME/.zshrc" ] && touch "$HOME/.zshrc"
    if [ -f "$HOME/.zshrc" ]; then
        grep -q "$BIN_DIR" "$HOME/.zshrc" 2>/dev/null || {
            printf '\n# Pre-built software\nexport PATH="%s:$PATH"\nexport PKG_CONFIG_PATH="%s"\n' \
                "$BIN_DIR" "$PC_DIR" >> "$HOME/.zshrc"
            echo "Added to ~/.zshrc"
        }
    fi
else
    echo "PATH already configured"
fi

# ---- 完成 ----
echo "Done: ${PKG_NAME} ${PKG_VERSION} installed to ${DEST}/"
echo "Run in new terminal: ${PKG_NAME} --version"
