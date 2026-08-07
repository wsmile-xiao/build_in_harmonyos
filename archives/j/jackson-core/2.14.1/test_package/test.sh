#!/usr/bin/env bash
# test.sh — jackson-core API 调用测试
# 编译并运行 Java 测试程序，调用 jackson-core JsonFactory/JsonParser API 解析 JSON
# 满足 R34 实质性验证要求

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -d "$candidate" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK found in common locations." >&2
    echo "Set JAVA_HOME to a JDK 17+ installation path." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

JAR_PATH="$PKG_DIR/libexec/jackson-core-2.14.1.jar"
TEST_SRC="$(dirname "$0")/TestJacksonCore.java"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== jackson-core API 调用测试 ==="

# 检查 JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: jackson-core JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

# 编译测试程序
if ! javac -cp "$JAR_PATH" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestJacksonCore.java compiled successfully"

# 运行测试程序
output=$(java -cp "$JAR_PATH:$TMP_DIR" TestJacksonCore 2>&1) || {
    echo "ERROR: Java test execution failed"
    echo "$output"
    exit 1
}

# 验证测试输出包含 PASS
if echo "$output" | grep -q "PASS"; then
    echo "OK: $output"
    echo "=== All tests passed ==="
    exit 0
else
    echo "ERROR: Test did not produce PASS output"
    echo "$output"
    exit 1
fi
