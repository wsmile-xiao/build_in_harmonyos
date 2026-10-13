#!/usr/bin/env bash
# test.sh — jakarta-annotation-api API 调用测试
# 编译并运行两个 Java 测试程序：
#   TestJakartaAnnotation     反射探针（40+ 断言，16 类型加载 + 元数据/默认值契约）
#   ConsumerAnnotationTest    最小注解驱动容器消费者用例（16 个 E2E 断言）
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

JAR_PATH="$PKG_DIR/libexec/jakarta.annotation-api-2.1.1.jar"
PROBE_SRC="$(dirname "$0")/TestJakartaAnnotation.java"
CONSUMER_SRC="$(dirname "$0")/ConsumerAnnotationTest.java"
# /tmp 在 OHOS 沙箱只读（EROFS），mktemp 失败时回退 $HOME
TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d "$HOME")"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "=== jakarta-annotation-api API 调用测试 ==="

# HarmonyOS PC 专项验证 1：确认运行时为 OHOS 环境时 JVM 正常执行
# （纯 Java jar 无平台 API 差异；专项在于确认 OHOS 上的 JVM 能加载并消费该 jar）
if [ -n "${CONAN_SDK_NATIVE:-}" ] || uname -a 2>/dev/null | grep -qi "ohos\|openharmony\|harmonyos"; then
    echo "OK: OHOS environment detected — running on-target jar consumption test"
fi

# 检查 JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: jakarta.annotation-api JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

# 编译探针 + 消费者用例（一次 javac 编译两个测试程序）
if ! javac -encoding UTF-8 -cp "$JAR_PATH" "$PROBE_SRC" "$CONSUMER_SRC" -d "$TMP_DIR" 2>&1; then
    echo "ERROR: javac compilation failed"
    exit 1
fi
echo "OK: TestJakartaAnnotation.java + ConsumerAnnotationTest.java compiled successfully"

# 运行反射探针测试程序
probe_output=$(java -cp "$JAR_PATH:$TMP_DIR" TestJakartaAnnotation 2>&1) || {
    echo "ERROR: probe execution failed"
    echo "$probe_output"
    exit 1
}

# 验证探针输出包含 PASS
if ! echo "$probe_output" | grep -q "PASS"; then
    echo "ERROR: probe did not produce PASS output"
    echo "$probe_output"
    exit 1
fi
echo "$probe_output"

# 运行最小容器消费者用例
consumer_output=$(java -cp "$JAR_PATH:$TMP_DIR" ConsumerAnnotationTest 2>&1) || {
    echo "ERROR: consumer E2E execution failed"
    echo "$consumer_output"
    exit 1
}
echo "$consumer_output"

# 验证消费者用例输出包含 SUMMARY 且 0 failed，以及最终 PASS
if ! echo "$consumer_output" | grep -q "E2E TEST SUMMARY: .* 0 failed"; then
    echo "ERROR: consumer E2E summary reports failures"
    exit 1
fi
if ! echo "$consumer_output" | grep -q "PASS:"; then
    echo "ERROR: consumer E2E did not produce PASS output"
    exit 1
fi
echo "=== All tests passed ==="
exit 0
