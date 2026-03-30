#!/bin/sh
# HarmonyOS 安装脚本模板
# 用法：sh install.sh [安装路径]
# 默认安装路径：$HOME/usr/

PACKAGE_NAME="{{SOFTWARE_NAME}}"
PACKAGE_VERSION="{{VERSION}}"
DEFAULT_INSTALL_DIR="$HOME/usr"

INSTALL_DIR="${1:-$DEFAULT_INSTALL_DIR}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR"

echo "========================================"
echo "安装 $PACKAGE_NAME $PACKAGE_VERSION"
echo "安装路径: $INSTALL_DIR/$PACKAGE_NAME"
echo "========================================"

# 检查
if [ ! -d "$PACKAGE_DIR/bin/" ]; then
    echo "❌ 错误：找不到 bin/ 目录"
    exit 1
fi

# 安装
mkdir -p "$INSTALL_DIR"
cp -r "$PACKAGE_DIR" "$INSTALL_DIR/$PACKAGE_NAME"

# 创建 wrapper 到 PATH
BIN_DIR="$INSTALL_DIR/$PACKAGE_NAME/bin"
for bin_file in "$BIN_DIR"/*; do
    [ -f "$bin_file" ] || continue
    name=$(basename "$bin_file")
    target="$INSTALL_DIR/bin/$name"
    
    # 不用软链接（SELinux 限制）
    mkdir -p "$INSTALL_DIR/bin"
    cat > "$target" << WEOF
#!/bin/sh
exec "$BIN_DIR/$name" "\$@"
WEOF
    chmod +x "$target"
done

# 预触发弹窗
echo "预触发二进制确认..."
for bin_file in "$BIN_DIR"/*; do
    [ -f "$bin_file" ] || continue
    "$bin_file" --version >/dev/null 2>&1 || true
done

echo ""
echo "✅ 安装完成！"
echo ""
echo "请将以下内容添加到 ~/.bashrc："
echo "  export PATH=\"$INSTALL_DIR/bin:\$PATH\""
echo ""
echo "然后运行："
echo "  source ~/.bashrc"
echo "  $PACKAGE_NAME --version"
