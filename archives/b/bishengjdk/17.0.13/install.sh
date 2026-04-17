#!/bin/sh
# BiSheng JDK 17.0.13 (self-signed for HarmonyOS) 安装脚本
set -e

PREFIX="${1:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing BiSheng JDK 17.0.13 (self-signed) for HarmonyOS..."
echo "Target: $PREFIX"

tar xzf "$SCRIPT_DIR/bishengjdk17-ohos-aarch64-runtime.tar.gz" -C "$PREFIX/"

echo ""
echo "Installed to: $PREFIX/bishengjdk17"
echo "Java: $PREFIX/bishengjdk17/bin/java"
$PREFIX/bishengjdk17/bin/java -version 2>&1 | head -1
echo ""
echo "✅ 此 JDK 已全量自签名，可直接 System.load JNI 库"
echo "   使用方式："
echo "   export JAVA_HOME=$PREFIX/bishengjdk17"
echo "   \$JAVA_HOME/bin/java -cp jna.jar:app.jar YourApp"
