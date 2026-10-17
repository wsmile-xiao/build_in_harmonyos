#!/usr/bin/env bash
# test.sh — jakarta-cdi-api API 调用测试
# 编译并运行 Java 反射测试程序，验证 cdi-api + lang-model 两个 JAR 完整可用
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

JAR_API="$PKG_DIR/libexec/jakarta.enterprise.cdi-api-4.0.1.jar"
JAR_MODEL="$PKG_DIR/libexec/jakarta.enterprise.lang-model-4.0.1.jar"
TEST_SRC="$(dirname "$0")/TestJakartaCdi.java"
# /tmp 在 OHOS 沙箱只读（EROFS），mktemp 失败时回退 $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== jakarta-cdi-api API 调用测试 ==="

# 检查两个 JAR 文件存在（api + lang-model，消费者需同时具备）
for jar in "$JAR_API" "$JAR_MODEL"; do
    if [ ! -f "$jar" ]; then
        echo "ERROR: JAR not found at $jar"
        exit 1
    fi
    echo "OK: JAR found at $jar"
done

# 编译测试程序（-encoding UTF-8：测试源码含中文注释）
if ! javac -encoding UTF-8 -cp "$JAR_API:$JAR_MODEL" "$TEST_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestJakartaCdi.java compiled successfully"

# 运行测试程序（两 jar 同在 classpath）
output=$(java -cp "$JAR_API:$JAR_MODEL:$TMP_DIR" TestJakartaCdi 2>&1) || {
    echo "ERROR: Java test execution failed"
    echo "$output"
    exit 1
}

# 验证测试输出包含 PASS
if echo "$output" | grep -q "^PASS:"; then
    echo "$output"
    echo "=== All tests passed ==="
    exit 0
else
    echo "ERROR: Test did not produce PASS output"
    echo "$output"
    exit 1
fi
