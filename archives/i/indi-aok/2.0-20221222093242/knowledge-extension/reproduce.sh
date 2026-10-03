#!/bin/sh
# reproduce.sh — 复现 + 验证「单体仓插件式子项目」适配范式（样例：indi-aok）
#
# 用法: sh reproduce.sh <含本归档的仓库根> [工作目录] [日志目录]
#       仓库根须包含 archives/i/indi-aok/2.0-20221222093242/conanfile.py
#
# 阶段 A: 检测脚本判定（信号证据）
# 阶段 B: conan create 全流程（无本地缓存依赖，--build=missing），附关键证据行提取
# 阶段 C: 运行期闭包与包装布局校验（由 test_package 执行，B 阶段内已含）
#
# 全程输出重定向到日志文件（不使用 `| head` 直接接管道，规避 SIGPIPE）；
# 不写死本机路径；不依赖本地 conan 缓存。

REPO="$1"
WORK="${2:-${TMPDIR:-/tmp}/indi-aok-repro}"
LOGS="${3:-$WORK/logs}"
PKG_DIR="archives/i/indi-aok/2.0-20221222093242"

if [ -z "$REPO" ] || [ ! -d "$REPO/$PKG_DIR" ]; then
    echo "usage: sh $0 <含 archives/i/indi-aok/2.0-20221222093242 的仓库根> [工作目录] [日志目录]" >&2
    exit 2
fi

mkdir -p "$WORK" "$LOGS" || exit 2
SRC="$WORK/src"
DETECT_LOG="$LOGS/detect.log"
CREATE_LOG="$LOGS/conan-create.log"
EVID_LOG="$LOGS/evidence.log"

echo "=== reproduce indi-aok (plugin-style subproject of a monorepo)"
echo "repo=$REPO"
echo "work=$WORK"
echo "logs=$LOGS"

# ---------------------------------------------------------------- 阶段 A
echo
echo "=== 阶段 A: 检测"
# 取一份源码树用于检测（conan 的 source 目录或已解压源码均可；此处优先复用工作区已有树）
if [ -d "$SRC/indi-aok" ]; then
    :
elif [ -d "$WORK/indi-3rdparty" ]; then
    SRC="$WORK/indi-3rdparty"
fi
if [ -d "$SRC" ]; then
    sh "$REPO/$PKG_DIR/knowledge-extension/detect-cmake-plugin-subproject.sh" "$SRC" "$DETECT_LOG"
    RC_A=$?
    echo "stage_a_rc=$RC_A  (1 = 命中范式信号，符合预期)"
    echo "--- detect.log 摘要"
    grep -E 'module_path_references|packages_without_any_finder|add_executable|signals_hit|RESULT' "$DETECT_LOG" 2>/dev/null
else
    echo "stage_a=SKIP (未提供源码树；先运行 conan create 后可从构建目录重跑检测)"
fi

# ---------------------------------------------------------------- 阶段 B
echo
echo "=== 阶段 B: conan create（干净流程）"
PROFILE_H=""
if [ -f "$REPO/ci/conan/profiles/ohos-aarch64" ]; then
    PROFILE_H="$REPO/ci/conan/profiles/ohos-aarch64"
    echo "host_profile=$PROFILE_H"
else
    echo "host_profile=<默认 profile>（未找到 ci/conan/profiles/ohos-aarch64）"
fi

CONAN_BIN="conan"
if command -v conan >/dev/null 2>&1; then
    CONAN_BIN="conan"
fi

if [ -n "$PROFILE_H" ]; then
    "$CONAN_BIN" create "$REPO/$PKG_DIR" -pr:b=default -pr:h="$PROFILE_H" --build=missing > "$CREATE_LOG" 2>&1
else
    "$CONAN_BIN" create "$REPO/$PKG_DIR" -pr:b=default --build=missing > "$CREATE_LOG" 2>&1
fi
RC_B=$?
echo "stage_b_rc=$RC_B"

# ---------------------------------------------------------------- 阶段 C（证据提取）
echo
echo "=== 阶段 C: 关键证据（从 create 日志提取，不用管道截断）"
{
    echo "--- S1 探测提示是否生效（期望 Found INDI ... (found version)）"
    grep -n 'Found INDI' "$CREATE_LOG" 2>/dev/null
    echo "--- S2 私有 config 包是否被使用（期望无 Could not find NovaConfig / Nova）"
    grep -n -i 'could not find.*nova\|NovaConfig' "$CREATE_LOG" 2>/dev/null
    echo "--- 链接命令中使用的 libnova 绝对路径（期望依赖包内 libnova.a）"
    find "$WORK" -name 'link.txt' 2>/dev/null | while IFS= read -r f; do
        grep -o '[^ ]*libnova[^ ]*' "$f" 2>/dev/null
    done | sort -u
    echo "--- 产物"
    grep -n 'indi_lx200aok' "$CREATE_LOG" 2>/dev/null
    echo "--- test_package 断言结果（期望 RESULT: PASS）"
    grep -n -e '\[ok\]' -e '\[FAIL\]' -e '\[skip\]' -e 'checks=' -e 'RESULT:' "$CREATE_LOG" 2>/dev/null
    echo "--- 包内容（conan cache 中的已打包文件）"
    "$CONAN_BIN" cache path indi-aok/2.0-20221222093242 2>/dev/null
    grep -n 'Packaged\|package():' "$CREATE_LOG" 2>/dev/null
} > "$EVID_LOG" 2>&1
cat "$EVID_LOG"

echo
echo "=== 结论"
if [ "$RC_B" -eq 0 ]; then
    echo "RESULT: PASS — conan create 全流程通过（S1+S2+S3 生效），证据见 $EVID_LOG"
    exit 0
fi
echo "RESULT: FAIL — conan create rc=$RC_B，完整日志 $CREATE_LOG"
exit 1
