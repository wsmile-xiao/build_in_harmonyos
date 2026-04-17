#!/bin/sh
# JNA 5.19.0 安装脚本 for HarmonyOS
set -e

PREFIX="${1:-$HOME/usr/local}"
JAR_NAME="jna.jar"

echo "Installing JNA 5.19.0 for HarmonyOS..."
echo "Target: $PREFIX"

# 创建目标目录
mkdir -p "$PREFIX/share/java"

# 安装 JAR
cp "$JAR_NAME" "$PREFIX/share/java/jna.jar"
echo "Installed: $PREFIX/share/java/jna.jar"

echo ""
echo "⚠️  注意：使用 JNA 需要已签名的 BiSheng JDK。"
echo "   如果尚未准备，请执行："
echo "   cp -a /data/service/hnp/bishengjdk17* \$HOME/usr/local/bishengjdk17"
echo "   python3 \$SKILL_ROOT/scripts/ohc-run.py sign-elf --batch \$HOME/usr/local/bishengjdk17"
echo ""
echo "使用方式："
echo "  java -cp $PREFIX/share/java/jna.jar:your-app.jar YourApp"
echo ""
echo "Done."
