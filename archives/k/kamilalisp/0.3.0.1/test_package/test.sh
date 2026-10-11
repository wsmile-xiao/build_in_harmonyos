#!/usr/bin/env bash
# test.sh — kamilalisp 0.3.0.1 消费者视角功能测试（R34 实质性验证）
# 通过打包后的 bin/kamilalisp CLI 启动器实际运行 KamilaLisp 解释器，
# 校验算术/字符串求值结果，并包含 1 个 HarmonyOS 平台专属断言。
set -uo pipefail

PKG_DIR="${1:-${CONAN_PACKAGE_FOLDER:-$(pwd)/package}}"
CLI="$PKG_DIR/bin/kamilalisp"
SCRIPT="$(dirname "$0")/test_kamilalisp.lisp"
JAR="$PKG_DIR/libexec/kamilalisp-0.3.jar"

# HMBS 沙箱：/tmp 只读，优先用 HMBS 注入的 TMPDIR/TMP/TEMP
WORK_TMP="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ -z "$WORK_TMP" ] || [ ! -d "$WORK_TMP" ] || [ ! -w "$WORK_TMP" ]; then
    WORK_TMP="$(pwd)/.tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null || WORK_TMP="$HOME/tmp"
    mkdir -p "$WORK_TMP" 2>/dev/null
fi
export TMPDIR="$WORK_TMP" TMP="$WORK_TMP" TEMP="$WORK_TMP"

# 解析 JAVA_HOME
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then
    for candidate in \
        /storage/Users/currentUser/bishengjdk17 \
        "$HOME/bishengjdk17" \
        /data/service/hnp/bishengjdk17 \
        /usr/lib/jvm/bishengjdk-17 \
        /usr/lib/jvm/java-17-openjdk-arm64; do
        if [ -x "$candidate/bin/java" ]; then JAVA_HOME="$candidate"; break; fi
    done
fi
if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then
    echo "ERROR: no JDK 17 found (set JAVA_HOME)" >&2
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":5,"passedCount":0}\n'
    exit 1
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

PASSED=0
FAILED=0
DISCOVERED=5
check() { # $1 = description
    if [ "$2" = "0" ]; then
        echo "PASS: $1"; PASSED=$((PASSED + 1))
    else
        echo "FAIL: $1"; FAILED=$((FAILED + 1))
    fi
}

echo "=== kamilalisp 0.3.0.1 CLI 功能测试 ==="

# TC1: CLI 启动器存在且可执行
[ -x "$CLI" ]; check "CLI launcher bin/kamilalisp present and executable" $?

# TC2: 运行解释器脚本，校验算术结果 (3 与 42)
OUT="$("$CLI" "$SCRIPT" 2>&1)"; RC=$?
echo "---- interpreter output ----"; echo "$OUT"; echo "----------------------------"
echo "$OUT" | grep -qx "3" && echo "$OUT" | grep -qx "42"; check "interpreter arithmetic (+ 1 2)=3, (* 6 7)=42" $?

# TC3: 字符串求值 (reverse "KamiLisp") = psiLimaK
echo "$OUT" | grep -qx "psiLimaK"; check 'string reverse "KamiLisp" -> psiLimaK' $?

# TC4 (HarmonyOS 专属): JVM 运行在 HarmonyOS 平台且为 BiSheng JDK 17
OSNAME="$("$JAVA_HOME/bin/java" -XshowSettings:properties -version 2>&1 | awk -F'= ' '/os\.name/{print $2}' | tr -d '\r')"
echo "JVM os.name = $OSNAME"
[ "$OSNAME" = "HarmonyOS" ]; check "HarmonyOS platform assertion (JVM os.name == HarmonyOS)" $?

# TC5: 解释器进程干净退出 (rc=0)
[ "$RC" = "0" ]; check "interpreter exits cleanly (rc=0)" $?

echo "=== $PASSED/$DISCOVERED assertions passed ==="
if [ "$FAILED" -eq 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASSED"
    exit 0
else
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' "$DISCOVERED" "$PASSED"
    exit 1
fi
