#!/usr/bin/env bash
# test.sh — jakarta-inject-api API 调用测试
# 编译并运行 Java 测试程序，反射加载 jakarta.inject 注解/接口验证 JAR 完整可用
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

JAR_PATH="$PKG_DIR/libexec/jakarta.inject-api-2.0.1.jar"
TEST_SRC="$(dirname "$0")/TestJakartaInject.java"
CONSUMER_SRC="$(dirname "$0")/ConsumerInjectTest.java"
# /tmp 在 OHOS 沙箱只读（EROFS），mktemp 失败时回退 $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== jakarta-inject-api API 调用测试 ==="

# 检查 JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: jakarta.inject-api JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

# 编译 API 探针 + 完整消费者用例（一次 javac 编译两个测试程序）
if ! javac -cp "$JAR_PATH" "$TEST_SRC" "$CONSUMER_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestJakartaInject.java + ConsumerInjectTest.java compiled successfully"

# 运行 API 探针测试程序
output=$(java -cp "$JAR_PATH:$TMP_DIR" TestJakartaInject 2>&1) || {
    echo "ERROR: Java test execution failed"
    echo "$output"
    exit 1
}

# 验证探针输出包含 PASS
if ! echo "$output" | grep -q "PASS"; then
    echo "ERROR: Test did not produce PASS output"
    echo "$output"
    exit 1
fi
echo "OK: $output"

# 运行完整消费者用例（最小 DI 容器端到端注入流程）
consumer_output=$(java -cp "$JAR_PATH:$TMP_DIR" ConsumerInjectTest 2>&1) || {
    echo "ERROR: consumer E2E execution failed"
    echo "$consumer_output"
    exit 1
}
echo "$consumer_output"

# 验证消费者用例输出包含 PASS
if ! echo "$consumer_output" | grep -q "PASS"; then
    echo "ERROR: consumer E2E did not produce PASS output"
    exit 1
fi
echo "OK: consumer E2E produced PASS"
echo "=== All tests passed ==="
exit 0
