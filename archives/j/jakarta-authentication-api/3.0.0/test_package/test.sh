#!/usr/bin/env bash
# test.sh — jakarta-authentication-api API 调用测试
# 编译并运行 Java 测试程序，反射加载 jakarta.security.auth.message
# 接口/类验证 JAR 完整可用，满足 R34 实质性验证要求

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

JAR_PATH="$PKG_DIR/libexec/jakarta.authentication-api-3.0.0.jar"
TEST_SRC="$(dirname "$0")/TestJakartaAuthentication.java"
FLOW_SRC="$(dirname "$0")/TestAuthFlow.java"
# /tmp 在 OHOS 沙箱只读（EROFS），mktemp 失败时回退 $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== jakarta-authentication-api API 调用测试 ==="

# 检查 JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: jakarta.authentication-api JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

# 编译测试程序（反射断言层 + E2E 消费者用例）
if ! javac -cp "$JAR_PATH" "$TEST_SRC" "$FLOW_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestJakartaAuthentication.java + TestAuthFlow.java compiled successfully"

# 运行反射断言测试程序（10 断言：8 类反射加载 + 2 项 SPI 契约）
output=$(java -cp "$JAR_PATH:$TMP_DIR" TestJakartaAuthentication 2>&1) || {
    echo "ERROR: Java reflection test execution failed"
    echo "$output"
    exit 1
}

# 验证反射断言输出包含 PASS
if echo "$output" | grep -q "PASS"; then
    echo "OK: $output"
else
    echo "ERROR: reflection test did not produce PASS output"
    echo "$output"
    exit 1
fi

# 运行 E2E 消费者测试（完整认证 SPI 流程：工厂注册→取回→config→context→
# validateRequest→SUCCESS→CallerPrincipalCallback 身份注入→生命周期收尾，
# 10 个测试用例每例独立 TEST PASS/FAIL 判定 + E2E TEST SUMMARY 汇总）
flow=$(java -cp "$JAR_PATH:$TMP_DIR" TestAuthFlow 2>&1) || {
    echo "ERROR: E2E consumer test execution failed"
    echo "$flow"
    exit 1
}
echo "$flow"

# 验证 E2E 测试：汇总 0 failed 且输出 PASS
if echo "$flow" | grep -q "E2E TEST SUMMARY: 10 passed, 0 failed" \
   && echo "$flow" | grep -q "PASS: E2E consumer test"; then
    echo "OK: E2E consumer test passed (10/10)"
    echo "=== All tests passed ==="
    exit 0
else
    echo "ERROR: E2E consumer test did not pass all cases"
    echo "$flow"
    exit 1
fi
