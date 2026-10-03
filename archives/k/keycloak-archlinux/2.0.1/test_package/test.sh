#!/usr/bin/env bash
# test.sh — keycloak-archlinux 主题 JAR 消费者验证
# 上游无测试套件（PKGBUILD 无 check()，.gitlab-ci.yml 仅 build job），
# 本测试做制品级实质验证（R34）：主题资源结构 + keycloak-themes.json 注册
# + JVM 真实加载探针。
#
# 注意：所有 jar 条目检查统一使用「unzip -l 落盘清单文件 + grep 文件」模式。
# 禁止 `unzip -l | grep -q` 管道写法——grep -q 匹配后提前退出使 unzip 收到
# SIGPIPE（exit 141），在 set -o pipefail 下整条管道非零，会随机误报
# （keycloak-metrics CI #50941 实锤该竞态）。

set -euo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"
JAR_PATH="$PKG_DIR/lib/keycloak-archlinux-theme.jar"

# 解析 JAVA_HOME：优先环境变量，其次检测常见 JDK 安装路径
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

echo "=== keycloak-archlinux theme JAR consumer test ==="

# 断言 1: JAR 文件存在
if [ ! -f "$JAR_PATH" ]; then
    echo "ERROR: keycloak-archlinux-theme JAR not found at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

# jar 条目清单一次性落盘（后续所有条目断言都 grep 这份文件，零管道零竞态）
unzip -l "$JAR_PATH" > "$TMP_DIR/jar_listing.txt"

# 断言 2: keycloak-themes.json 主题注册文件（Keycloak provider 加载入口）
unzip -p "$JAR_PATH" "META-INF/keycloak-themes.json" > "$TMP_DIR/themes.json" 2>/dev/null
if ! grep -q "archlinux" "$TMP_DIR/themes.json"; then
    echo "ERROR: keycloak-themes.json missing or does not register 'archlinux' theme"
    exit 1
fi
echo "OK: keycloak-themes.json registers archlinux theme: $(cat "$TMP_DIR/themes.json")"

# 断言 3-7: 五个主题子类型的关键资源齐全（login/account/admin/email/welcome）
check_entry() {
    if ! grep -qF "$2" "$TMP_DIR/jar_listing.txt"; then
        echo "ERROR: JAR entry missing: $2"
        exit 1
    fi
    echo "OK: $1"
}
check_entry "login override page (register.ftl)"       "theme/archlinux/login/register.ftl"
check_entry "login override page (terms.ftl)"          "theme/archlinux/login/terms.ftl"
check_entry "login override page (login-config-totp)"  "theme/archlinux/login/login-config-totp.ftl"
check_entry "account theme page (index.ftl)"           "theme/archlinux/account/index.ftl"
check_entry "welcome theme page (index.ftl)"           "theme/archlinux/welcome/index.ftl"

# 断言 8-10: 主题属性与 i18n 资源
check_entry "login theme.properties"                    "theme/archlinux/login/theme.properties"
check_entry "login i18n messages_en.properties"         "theme/archlinux/login/messages/messages_en.properties"
check_entry "email i18n messages_en.properties"         "theme/archlinux/email/messages/messages_en.properties"

# 断言 11-12: 主题静态资源（品牌图片）
check_entry "archlinux logo svg"                        "archlinux-logo-light.svg"
check_entry "login background image"                    "login-background.jpg"

# 断言 13: JAR MANIFEST 存在
if ! grep -qF "META-INF/MANIFEST.MF" "$TMP_DIR/jar_listing.txt"; then
    echo "ERROR: META-INF/MANIFEST.MF missing"
    exit 1
fi
echo "OK: JAR MANIFEST present"

# 断言 14: JVM 真实加载探针（URLClassLoader 读取主题资源，R34 实质性验证；
# 探针内部再校验 3 个资源可读 + themes.json 内容，覆盖口径合计 17，
# 与 test_package/MANIFEST.yml assertion_count 一致）
cat > "$TMP_DIR/TestLoadTheme.java" <<'JEOF'
import java.io.InputStream;
import java.net.URL;
import java.net.URLClassLoader;
import java.nio.charset.StandardCharsets;

public class TestLoadTheme {
    public static void main(String[] args) throws Exception {
        URL jarUrl = new java.io.File(args[0]).toURI().toURL();
        try (URLClassLoader cl = new URLClassLoader(new URL[]{jarUrl},
                TestLoadTheme.class.getClassLoader())) {
            String[] required = {
                "theme/archlinux/account/index.ftl",
                "theme/archlinux/login/theme.properties",
                "META-INF/keycloak-themes.json",
            };
            for (String res : required) {
                URL u = cl.getResource(res);
                if (u == null)
                    throw new AssertionError("resource not visible in jar: " + res);
                try (InputStream in = cl.getResourceAsStream(res)) {
                    int n = in.read();
                    if (n < 0)
                        throw new AssertionError("resource empty: " + res);
                }
            }
            // keycloak-themes.json 内容可读且声明 archlinux 主题
            String json;
            try (InputStream in = cl.getResourceAsStream("META-INF/keycloak-themes.json");
                 java.io.ByteArrayOutputStream buf = new java.io.ByteArrayOutputStream()) {
                byte[] b = new byte[4096];
                int r;
                while ((r = in.read(b)) > 0) buf.write(b, 0, r);
                json = new String(buf.toByteArray(), StandardCharsets.UTF_8);
            }
            if (!json.contains("archlinux"))
                throw new AssertionError("keycloak-themes.json does not declare archlinux");
        }
        System.out.println("PASS");
    }
}
JEOF
javac -d "$TMP_DIR" "$TMP_DIR/TestLoadTheme.java"
output=$(java -cp "$TMP_DIR" TestLoadTheme "$JAR_PATH")
if ! grep -q "PASS" <<< "$output"; then
    echo "ERROR: JVM theme load test failed"
    echo "$output"
    exit 1
fi
echo "OK: JVM load probe: $output"

echo "=== All tests passed ==="
exit 0
