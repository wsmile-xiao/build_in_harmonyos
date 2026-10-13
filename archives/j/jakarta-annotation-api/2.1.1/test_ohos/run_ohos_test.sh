#!/bin/sh
# test_ohos — jakarta-annotation-api 2.1.1 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 本库为纯 Java 注解 jar（无 native/JNI/平台条件源码），HarmonyOS PC 专项采用
# 「目标平台 JVM + 最终 Conan 包 jar 消费」方式，整体计 1 项逻辑测试：
#
#   T1  定位 test_package 实际使用的 java 可执行文件（对齐 test_package/
#       conanfile.py 的 JAVA_HOME 探测链——conan test() 将 $JAVA_HOME/bin
#       前置到 PATH，实际 java 即 $JAVA_HOME/bin/java），并解析 symlink 链
#       至真实二进制；输出 java -version 证据。找不到即明确失败。
#   T2  真实 java 二进制为 ELF64（readelf/llvm-readelf/llvm-readobj；
#       检查工具缺失时明确失败退出，绝不 SKIP 后返回成功。若 launcher 非
#       ELF，打印首字节诊断，需先沿真实启动链找到最终 native launcher
#       再验证——不降低检查标准）
#   T3  Machine: AArch64
#   T4  动态 ELF 时 PT_INTERP 必须为 musl AArch64 loader（ld-musl-aarch64）；
#       静态 ELF（无 PT_INTERP）则无需 loader 断言
#   T5  在该已确认的 HarmonyOS AArch64 JVM 下，用最终 Conan 包中的
#       jakarta.annotation-api jar 编译并运行最小消费者 OhosConsumer：
#       JVM 自报 os.name=HarmonyOS / os.arch=aarch64，并真实消费
#       @Resource / @PostConstruct / @PreDestroy / @Priority
#
# 用法：sh run_ohos_test.sh <conan 包目录>（含 libexec/jakarta.annotation-api-2.1.1.jar）
# 退出码：0=全部通过；非 0=有失败。
set -u

PKG="${1:-}"
JAR_NAME="jakarta.annotation-api-2.1.1.jar"
[ -n "$PKG" ] || { echo "usage: $0 <conan-package-dir>"; exit 2; }
JAR="$PKG/libexec/$JAR_NAME"
[ -f "$JAR" ] || { echo "FAIL: final package jar not found: $JAR"; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONSUMER_SRC="$SCRIPT_DIR/OhosConsumer.java"
[ -f "$CONSUMER_SRC" ] || { echo "FAIL: consumer source not found: $CONSUMER_SRC"; exit 2; }

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- jakarta-annotation-api 2.1.1 HarmonyOS PC 专项验证 (pkg=$PKG) ---"
echo "方式: 目标平台 JVM + 最终 Conan 包 jar 消费（纯 Java 库无 native/JNI，不伪造平台 API 专项）"

# ELF 检查工具 fail-closed：缺失即明确失败退出（绝不 SKIP 后返回成功）
ELF_H=""; ELF_L=""
if command -v readelf >/dev/null 2>&1; then
    ELF_H="readelf -h"; ELF_L="readelf -l"
elif command -v llvm-readelf >/dev/null 2>&1; then
    ELF_H="llvm-readelf -h"; ELF_L="llvm-readelf -l"
elif command -v llvm-readobj >/dev/null 2>&1; then
    # llvm-readobj 默认 LLVM 风格，需切 GNU 风格才能 grep Class/Machine/INTERP
    ELF_H="llvm-readobj --elf-output-style=GNU --file-headers"
    ELF_L="llvm-readobj --elf-output-style=GNU --program-headers"
else
    echo "FAIL: readelf/llvm-readelf/llvm-readobj 均不可用，ELF 平台断言无法执行（fail-closed，不 SKIP）"
    exit 1
fi
echo "ELF 检查工具: $ELF_H / $ELF_L"

# T1: 定位 test_package 实际使用的 java（对齐 test_package/conanfile.py 探测链）
JAVA_HOME_SRC=""
if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/java" ]; then
    JAVA_HOME_SRC="环境变量 JAVA_HOME=$JAVA_HOME"
else
    for candidate in \
        "$HOME/bishengjdk17" \
        "$HOME/usr/local/bishengjdk17" \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -x "$candidate/bin/java" ]; then
            JAVA_HOME="$candidate"
            JAVA_HOME_SRC="探测链命中 $candidate"
            break
        fi
    done
fi
if [ -n "$JAVA_HOME_SRC" ]; then
    chk "T1 定位 test_package 使用 java（$JAVA_HOME_SRC）" 0
else
    chk "T1 定位 test_package 使用 java（JAVA_HOME 探测链，对齐 test_package/conanfile.py）" 1
    echo "  JAVA_HOME 未设置且候选路径均无 bin/java（test_package 同链会直接 Exception，此处 fail-closed）"
    exit 1
fi

# 解析 symlink 链至真实二进制（必要时；如 usr/local/bin/java → bishengjdk17/bin/java）
JAVA_BIN="$JAVA_HOME/bin/java"; JAVA_LINKS=""
i=0
while [ -L "$JAVA_BIN" ] && [ "$i" -lt 10 ]; do
    tgt=$(readlink "$JAVA_BIN")
    case "$tgt" in
        /*) JAVA_BIN="$tgt" ;;
        *) JAVA_BIN="$(dirname "$JAVA_BIN")/$tgt" ;;
    esac
    JAVA_LINKS="$JAVA_LINKS -> $JAVA_BIN"
    i=$((i+1))
done
[ -f "$JAVA_BIN" ] || { echo "FAIL: java symlink 解析失败: $JAVA_BIN"; exit 1; }
echo "  java: $JAVA_HOME/bin/java${JAVA_LINKS:+（symlink 解析:$JAVA_LINKS）}"
"$JAVA_BIN" -version 2>&1 | sed -n '1,3p' | sed 's/^/  /'

# T2: 真实 java 二进制为 ELF64
HDR=$($ELF_H "$JAVA_BIN" 2>&1)
if echo "$HDR" | grep -q "Class:.*ELF64"; then
    chk "T2 java 真实二进制为 ELF64（Class: ELF64）" 0
else
    echo "  ELF header 输出前 5 行:"; echo "$HDR" | sed -n '1,5p' | sed 's/^/    /'
    echo "  首字节: $(head -c 4 "$JAVA_BIN" 2>/dev/null | od -An -tx1 2>/dev/null)（ELF 魔数应为 7f 45 4c 46）"
    echo "  若 launcher 为脚本/包装器：需沿真实启动链找到最终 native launcher 后重验，不降级标准"
    chk "T2 java 真实二进制为 ELF64（Class: ELF64）" 1
fi

# T3: AArch64
if echo "$HDR" | grep -q "Machine:.*AArch64"; then
    chk "T3 java 为 AArch64（Machine: AArch64）" 0
else
    echo "  Machine: $(echo "$HDR" | grep 'Machine:')"
    chk "T3 java 为 AArch64（Machine: AArch64）" 1
fi

# T4: 动态 ELF 时 PT_INTERP 必须为 musl AArch64 loader
PH=$($ELF_L "$JAVA_BIN" 2>&1)
if echo "$PH" | grep -q "INTERP"; then
    INTERP_LINE=$(echo "$PH" | grep "Requesting program interpreter" | head -1)
    if echo "$INTERP_LINE" | grep -q "musl-aarch64"; then
        chk "T4 动态 ELF: PT_INTERP 为 musl AArch64 loader（$INTERP_LINE）" 0
    else
        echo "  实际 interpreter: $INTERP_LINE"
        chk "T4 动态 ELF: PT_INTERP 为 musl AArch64 loader" 1
    fi
else
    chk "T4 静态 ELF（无 PT_INTERP，无需 loader 断言）" 0
fi

# T5: 已确认的 HarmonyOS AArch64 JVM 下，最终包 jar 编译 + 运行最小消费者
JAVAC_BIN="$JAVA_HOME/bin/javac"
[ -x "$JAVAC_BIN" ] || { echo "FAIL: javac not found: $JAVAC_BIN"; exit 1; }

# /tmp 在 OHOS 沙箱可能只读（EROFS），mktemp 失败回退 $HOME
WORK="$(mktemp -d 2>/dev/null || true)"
if [ -z "$WORK" ] || [ ! -d "$WORK" ]; then
    WORK="$HOME/.jakarta-annotation-api-ohos-test.$$"
    rm -rf "$WORK"; mkdir -p "$WORK" || { echo "FAIL: 无法创建工作目录 $WORK"; exit 1; }
fi
trap 'rm -rf "$WORK"' EXIT

if "$JAVAC_BIN" -encoding UTF-8 -cp "$JAR" "$CONSUMER_SRC" -d "$WORK" >"$WORK/javac.log" 2>&1; then
    echo "  javac 编译 OhosConsumer.java OK（classpath = 最终包 jar）"
    COUT=$("$JAVA_BIN" -cp "$JAR:$WORK" OhosConsumer 2>&1); CRC=$?
    echo "$COUT" | sed 's/^/  /'
    if [ "$CRC" = "0" ] && echo "$COUT" | grep -q "OHOS consumer OK"; then
        chk "T5 最终包 jar 真机消费：HarmonyOS aarch64 JVM 下编译+运行 OhosConsumer（@Resource/@PostConstruct/@PreDestroy/@Priority）" 0
    else
        chk "T5 最终包 jar 真机消费（rc=$CRC，输出需含 OHOS consumer OK）" 1
    fi
else
    sed -n '1,10p' "$WORK/javac.log" | sed 's/^/  /'
    chk "T5 javac 编译消费者（最终包 jar classpath）" 1
fi

# 汇总：本脚本整体为 1 项逻辑测试（内部 T1–T5 平台断言不重复计数）
if [ "$fail" = "0" ]; then
    echo "PASS: jakarta-annotation-api HarmonyOS PC 专项 - 1 logical test (target-platform JVM + final package jar consumption)"
    echo "--- jakarta-annotation-api OHOS 专项: ALL PASS (1/1) ---"
else
    echo "--- jakarta-annotation-api OHOS 专项: FAILED ---"
fi
exit "$fail"
