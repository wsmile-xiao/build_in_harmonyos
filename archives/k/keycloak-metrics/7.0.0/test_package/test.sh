#!/usr/bin/env bash
# test.sh — keycloak-metrics 消费者验证
# 验证 fat jar 的 SPI 注册文件与 prometheus shading 完整性（R34 实质性验证）
#
# 注意：所有 jar 条目检查统一使用「unzip -l 落盘清单文件 + grep 文件」模式。
# 禁止 `unzip -l | grep -q` 管道写法——grep -q 匹配后提前退出使 unzip 收到
# SIGPIPE（exit 141），在 set -o pipefail 下整条管道非零，会以约 25% 概率
# 随机误报"not shaded / missing"（匹配行在清单中的位置决定竞态窗口）。
# CI #50941 与本机复现均实锤该竞态。

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"
JAR_PATH="$PKG_DIR/libexec/keycloak-metrics-spi-6.0.1-SNAPSHOT.jar"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径
# （cmd-pkgs install-jdk.sh 的标准安装位置是 ~/bishengjdk17）
if [ -z "${JAVA_HOME:-}" ] || [ ! -d "$JAVA_HOME" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
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
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

echo "=== keycloak-metrics SPI jar 消费者测试 ==="

# 断言 1: JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: keycloak-metrics JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# jar 条目清单一次性落盘（后续所有条目断言都 grep 这份文件，零管道零竞态）
unzip -l "$JAR_PATH" > "$TMP_DIR/jar_listing.txt"

# 断言 2: SPI 注册文件 — EventListenerProviderFactory
unzip -p "$JAR_PATH" "META-INF/services/org.keycloak.events.EventListenerProviderFactory" > "$TMP_DIR/elf" 2>/dev/null
if ! grep -q "MetricsEventListenerFactory" "$TMP_DIR/elf"; then
    echo "ERROR: EventListenerProviderFactory SPI registration missing/wrong"
    exit 1
fi
echo "OK: EventListenerProviderFactory SPI registered -> $(cat "$TMP_DIR/elf")"

# 断言 3: SPI 注册文件 — RealmResourceProviderFactory
unzip -p "$JAR_PATH" "META-INF/services/org.keycloak.services.resource.RealmResourceProviderFactory" > "$TMP_DIR/rrp" 2>/dev/null
if ! grep -q "MetricsEndpointFactory" "$TMP_DIR/rrp"; then
    echo "ERROR: RealmResourceProviderFactory SPI registration missing/wrong"
    exit 1
fi
echo "OK: RealmResourceProviderFactory SPI registered -> $(cat "$TMP_DIR/rrp")"

# 断言 4: prometheus simpleclient 已 shade 进 fat jar
if ! grep -q "io/prometheus/client/CollectorRegistry.class" "$TMP_DIR/jar_listing.txt"; then
    echo "ERROR: prometheus CollectorRegistry not shaded into fat jar"
    exit 1
fi
echo "OK: prometheus simpleclient shaded (CollectorRegistry present)"

# 断言 5: 本插件自身 class 齐全
for cls in MetricsEndpoint MetricsEndpointFactory MetricsEventListener \
           MetricsEventListenerFactory PrometheusExporter; do
    if ! grep -q "org/jboss/aerogear/keycloak/metrics/${cls}.class" "$TMP_DIR/jar_listing.txt"; then
        echo "ERROR: plugin class $cls missing from jar"
        exit 1
    fi
done
echo "OK: 5 plugin classes present"

# 断言 6: jar 可被 JVM 正常加载（verify 结构完整性，不执行 Keycloak 运行时）
cat > "$TMP_DIR/TestLoadJar.java" <<'JEOF'
import java.net.URL;
import java.net.URLClassLoader;

public class TestLoadJar {
    public static void main(String[] args) throws Exception {
        URL jarUrl = new java.io.File(args[0]).toURI().toURL();
        try (URLClassLoader cl = new URLClassLoader(new URL[]{jarUrl},
                TestLoadJar.class.getClassLoader())) {
            // 加载被 shade 的 prometheus 类（fat jar 消费者视角）
            Class<?> reg = Class.forName("io.prometheus.client.CollectorRegistry", false, cl);
            if (reg == null) throw new AssertionError("CollectorRegistry not loadable");
            // 加载插件 SPI 实现类（keycloak-api 为 provided，不在 classpath，
            // 只验证本 jar 内类资源可见性：通过 getResource 检查字节码存在）
            String res = "org/jboss/aerogear/keycloak/metrics/PrometheusExporter.class";
            if (cl.getResource(res) == null)
                throw new AssertionError("PrometheusExporter.class not visible in jar");
        }
        System.out.println("PASS");
    }
}
JEOF
javac -d "$TMP_DIR" "$TMP_DIR/TestLoadJar.java"
output=$(java -cp "$TMP_DIR" TestLoadJar "$JAR_PATH")
if ! echo "$output" | grep -q "PASS"; then
    echo "ERROR: JVM load test failed"
    echo "$output"
    exit 1
fi
echo "OK: $output"

echo "=== All tests passed ==="
exit 0
