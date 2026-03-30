#!/bin/sh
# HarmonyOS 卸载脚本模板

PACKAGE_NAME="{{SOFTWARE_NAME}}"
DEFAULT_INSTALL_DIR="$HOME/usr"

INSTALL_DIR="${1:-$DEFAULT_INSTALL_DIR}"

echo "即将删除：$INSTALL_DIR/$PACKAGE_NAME"
echo "以及 $INSTALL_DIR/bin/ 下的相关 wrapper 脚本"
echo ""
read -p "确认卸载？(y/N) " confirm
[ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || { echo "已取消"; exit 0; }

# 删除包装目录
rm -rf "$INSTALL_DIR/$PACKAGE_NAME"
echo "✅ 已删除 $INSTALL_DIR/$PACKAGE_NAME"

# 清理 wrapper（保守策略：只删除明确属于此包的）
if [ -d "$INSTALL_DIR/bin" ]; then
    for wrapper in "$INSTALL_DIR/bin/"*; do
        [ -f "$wrapper" ] || continue
        if grep -q "$INSTALL_DIR/$PACKAGE_NAME" "$wrapper" 2>/dev/null; then
            rm -f "$wrapper"
            echo "  已清理 $(basename "$wrapper")"
        fi
    done
fi

echo ""
echo "⚠️ 请手动从 ~/.bashrc 中移除相关 PATH 配置"
