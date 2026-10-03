#!/bin/sh
# detect-cmake-plugin-subproject.sh — 识别「单体仓插件式子项目」的三类共性适配点
#
# 用法: sh detect-cmake-plugin-subproject.sh <源码目录> [日志文件]
#   退出码: 0 = 未命中；1 = 命中（需按 strategy.md 的 S1/S2/S3 处理）；2 = 用法错误
#
# 纯 POSIX sh：不使用数组/[[ ]]/进程替换，输出全部重定向到日志文件（规避 SIGPIPE）。
# 脚本不写死任何本机绝对路径，也不读 conan 缓存（只读传入的源码目录）。

SRC="$1"
LOG="${2:-}"

if [ -z "$SRC" ]; then
    echo "usage: sh $0 <源码目录> [日志文件]" >&2
    exit 2
fi
if [ ! -d "$SRC" ]; then
    echo "error: not a directory: $SRC" >&2
    exit 2
fi

if [ -n "$LOG" ]; then
    exec > "$LOG" 2>&1
fi

HITS=0
# 鸿蒙 PC 上 /tmp 可能只读（E002），临时文件优先落 TMPDIR
TMPF=$(mktemp 2>/dev/null || echo "${TMPDIR:-${HOME:-.}}/.detect-names.$$")
echo "=== detect-cmake-plugin-subproject.sh"
echo "src=$SRC"
echo "date=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"

# ---------------------------------------------------------------- 信号 1
echo
echo "--- 信号 1: 仓库级 cmake_modules（模块模式探测，conan config 包不可替代）"
MOD_HITS=$(grep -rIn --include=CMakeLists.txt --include='*.cmake' \
    -e 'APPEND CMAKE_MODULE_PATH' -e '\.\./cmake_modules' "$SRC" 2>/dev/null | wc -l)
echo "module_path_references=$MOD_HITS"
grep -rIn --include=CMakeLists.txt --include='*.cmake' \
    -e 'APPEND CMAKE_MODULE_PATH' -e '\.\./cmake_modules' "$SRC" 2>/dev/null | head -10
if [ "$MOD_HITS" -gt 0 ]; then
    HITS=$((HITS + 1))
    echo "verdict=HIT  (模块模式 find_package 需由配方注入探测提示, 见 strategy.md S1)"
fi

# ---------------------------------------------------------------- 信号 2
echo
echo "--- 信号 2: find_package 请求的模块在树内是否有 Find<Name>.cmake"
grep -rhoE 'find_package[[:space:]]*\([[:space:]]*[A-Za-z0-9_-]+' \
    --include=CMakeLists.txt --include='*.cmake' "$SRC" 2>/dev/null \
    | sed -e 's/.*(//' | sort -u > "$TMPF" 2>/dev/null || true
if [ -s "$TMPF" ]; then
    MISSING=0
    while IFS= read -r NAME; do
        MODFILE=$(find "$SRC" -name "Find$NAME.cmake" 2>/dev/null | head -1)
        CFGFILE=$(find "$SRC" \( -name "$NAME""Config.cmake" -o -name "$(echo "$NAME" | tr 'A-Z' 'a-z')-config.cmake" \) 2>/dev/null | head -1)
        if [ -n "$MODFILE" ]; then
            echo "package=$NAME  module=$MODFILE"
        elif [ -n "$CFGFILE" ]; then
            echo "package=$NAME  config=$CFGFILE"
        else
            echo "package=$NAME  module=NONE config=NONE  <-- 需确认依赖包是否提供 $NAME""Config.cmake"
            MISSING=$((MISSING + 1))
        fi
    done < "$TMPF"
    rm -f "$TMPF"
    echo "packages_without_any_finder=$MISSING"
    if [ "$MISSING" -gt 0 ]; then
        HITS=$((HITS + 1))
        echo "verdict=HIT  (缺失的 finder 只能由配方生成私有 config 包, 见 strategy.md S2)"
    fi
else
    echo "package=none"
fi

# ---------------------------------------------------------------- 信号 3
echo
echo "--- 信号 3: CMake 策略下限与 C++ 标准（与预编译依赖代次是否匹配）"
grep -rIn --include=CMakeLists.txt --include='*.cmake' -e 'cmake_minimum_required' "$SRC" 2>/dev/null | head -10
echo "-- CMake 4.x 拒绝 cmake_minimum_required < 3.5："
grep -rhoE 'cmake_minimum_required[[:space:]]*\([[:space:]]*VERSION[[:space:]]+[0-9.]+' \
    --include=CMakeLists.txt --include='*.cmake' "$SRC" 2>/dev/null \
    | sed -e 's/.*VERSION[[:space:]]*//' | sort -u | head -5
echo "-- CMAKE_CXX_STANDARD："
grep -rIn --include=CMakeLists.txt --include='*.cmake' -e 'CMAKE_CXX_STANDARD' "$SRC" 2>/dev/null | head -5

# ---------------------------------------------------------------- 信号 4
echo
echo "--- 信号 4: 插件式可执行文件（被主程序 dlopen，需运行期闭包校验）"
EXE_HITS=$(grep -rIn --include=CMakeLists.txt -e 'add_executable' "$SRC" 2>/dev/null | wc -l)
BIN_INSTALL=$(grep -rIn --include=CMakeLists.txt -e 'RUNTIME DESTINATION bin' "$SRC" 2>/dev/null | wc -l)
echo "add_executable=$EXE_HITS  runtime_destination_bin=$BIN_INSTALL"
if [ "$EXE_HITS" -gt 0 ] && [ "$BIN_INSTALL" -gt 0 ]; then
    HITS=$((HITS + 1))
    echo "verdict=HIT  (打包物为 bin/ 可执行文件, test_package 须真跑并区分包装缺陷/平台限制, 见 strategy.md S5)"
fi

# ---------------------------------------------------------------- 汇总
echo
echo "=== summary"
echo "signals_hit=$HITS"
if [ "$HITS" -gt 0 ]; then
    echo "RESULT: HIT — 按 strategy.md 的 S1(探测提示) / S2(私有 config 包) / S3(代次对齐) 处理"
    exit 1
fi
echo "RESULT: NONE — 未命中本范式特征"
exit 0
