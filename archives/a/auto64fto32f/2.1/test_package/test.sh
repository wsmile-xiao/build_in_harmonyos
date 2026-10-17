#!/usr/bin/env bash
# test.sh — auto64fto32f 2.1 API 调用测试（消费者视角，R34 实质性验证）
# 编译并运行 TestAuto64Fto32F.java，调用被测 JAR 的
# AugmentJavaFiles / ConvertFile32From64 / RecursiveConvert API。

set -uo pipefail

# HMBS 沙箱：/tmp 只读，优先使用 HMBS 注入的 TMPDIR/TMP/TEMP
WORK_TMP="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ -z "$WORK_TMP" ] || [ ! -d "$WORK_TMP" ] || [ ! -w "$WORK_TMP" ]; then
    WORK_TMP="$(pwd)/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || WORK_TMP="$(dirname "$0")/.tmp"
    mkdir -p "$WORK_TMP"
fi
export TMPDIR="$WORK_TMP" TMP="$WORK_TMP" TEMP="$WORK_TMP"

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"

# 解析 JAVA_HOME：环境变量优先，其次 cmd-pkgs 标准安装路径
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "$JAVA_HOME/bin/java" ]; then
    for candidate in \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
        /storage/Users/currentUser/usr/local/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -f "$candidate/bin/java" ]; then
            JAVA_HOME="$candidate"
            break
        fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -f "${JAVA_HOME:-}/bin/javac" ]; then
    echo "ERROR: JAVA_HOME not set and no JDK (with javac) found in common locations." >&2
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

JAR_PATH="$PKG_DIR/libexec/auto64fto32f-2.1.jar"
TEST_SRC="$(dirname "$0")/TestAuto64Fto32F.java"

TMP_DIR="$(mktemp -d "$WORK_TMP/a64f.XXXXXX" 2>/dev/null)" || {
    TMP_DIR="$WORK_TMP/a64f.$$"
    mkdir -p "$TMP_DIR"
}

echo "=== auto64fto32f 2.1 API 调用测试 ==="

if [ ! -f "$JAR_PATH" ] || [ ! -s "$JAR_PATH" ]; then
    echo "ERROR: packaged JAR not found or empty at $JAR_PATH"
    exit 1
fi
echo "OK: JAR found at $JAR_PATH ($(wc -c < "$JAR_PATH") bytes)"

# 编译消费者测试程序（真实调用被测包 API）
if ! javac -encoding UTF-8 -cp "$JAR_PATH" -d "$TMP_DIR" "$TEST_SRC"; then
    echo "ERROR: javac compilation failed against packaged JAR"
    exit 1
fi
echo "OK: TestAuto64Fto32F.java compiled successfully against the package JAR"

# 运行并捕获输出与退出码
set +e
output=$(java -cp "$JAR_PATH:$TMP_DIR" TestAuto64Fto32F 2>&1)
rc=$?
set -u
printf '%s\n' "$output"

line=$(printf '%s\n' "$output" | grep '^AUTO64FTO32F_TEST_PASS ' | tail -n 1)
counts=${line#AUTO64FTO32F_TEST_PASS }
passed_count=${counts%%/*}
total_count=${counts##*/}

case "$counts" in
    */*) : ;;
    *) passed_count=0; total_count=0 ;;
esac

rm -rf "$TMP_DIR" 2>/dev/null

if [ "$rc" -eq 0 ] && [ "$total_count" -gt 0 ] 2>/dev/null \
   && [ "$passed_count" = "$total_count" ]; then
    echo "=== All $passed_count/$total_count consumer checks passed ==="
    # HMBS 机器门禁：test_package 结束后产出一行合法 JSON 标记，
    # discovered/passedCount 来自测试程序实际执行的断言计数（非桩值）。
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":%s,"passedCount":%s}\n' \
        "$total_count" "$passed_count"
    exit 0
else
    echo "ERROR: consumer test failed (rc=$rc, passed=$passed_count/$total_count)"
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":%s,"passedCount":%s}\n' \
        "$total_count" "$passed_count"
    exit 1
fi
