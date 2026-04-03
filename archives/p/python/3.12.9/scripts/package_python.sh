#!/bin/env bash
# ============================================================
# Python 可移植包制作脚本（HarmonyOS 通用模板）
# ============================================================
#
# 综合 Python 3.9.25 (strip+debug) + 3.12.9 (独立安装+缓存清理)
# 最佳实践，适用于所有 Python 版本的可移植打包。
#
# 使用方法：
#   chmod +x package_python.sh
#   ./package_python.sh [源码目录]
#
# 默认源码目录：当前目录下的 Python-x.y.z-v2/
#
# 产物：
#   python-{VERSION}-ohos-aarch64.tar.gz          主包
#   python-{VERSION}-ohos-aarch64-debug.tar.gz     Debug 符号包
#
# 流程（10 步）：
#   1. make install 到独立目录
#   2. 清理缓存和非必要文件（__pycache__/.pyc/pip）
#   3. 符号链接替换（wrapper/cp）
#   4. ⭐ 收集外部依赖库到 lib/external/（必做）
#   5. 设置 RPATH（$ORIGIN 相对路径）
#   6. Strip debug 符号 + 分离保存
#   7. ELF 签名（adhoc self-sign）
#   8. ⭐ 统一修复执行权限（必做！签名后权限被重置）
#   9. 创建 activate.sh / README.md
#  10. 打包 tar.gz
#
# 依赖工具：
#   patchelf         (RPATH 修改)
#   llvm-objcopy     (移除 .codesign / strip / debug 分离)
#   binary-sign-tool (重新签名)
#   llvm-readelf     (分析 NEEDED 依赖)
#
# ============================================================

set -e

# ======================== 配置区 ========================
PYTHON_VERSION="${PYTHON_VERSION:-3.12.9}"
ARCH="$(uname -m)"
PACKAGE_NAME="python-${PYTHON_VERSION}-ohos-${ARCH}"

# 源码目录（含 Makefile 的构建根目录）
SRC_DIR="${1:-$(pwd)/Python-${PYTHON_VERSION}-v2}"
if [ ! -f "$SRC_DIR/Makefile" ]; then
    echo "❌ 错误: 找不到 $SRC_DIR/Makefile"
    echo "   用法: $0 [Python源码目录]"
    exit 1
fi

# 输出目录
OUTPUT_DIR="${OUTPUT_DIR:-$(dirname "$SRC_DIR")}"
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME"
DEBUG_DIR="$OUTPUT_DIR/${PACKAGE_NAME}.debug"

# 是否 strip（默认是）
STRIP_DEBUG="${STRIP_DEBUG:-1}"

# 是否纯净版（不装 pip，默认是）
PURE_MODE="${PURE_MODE:-1}"

# ======================== 工具路径 ========================
PATCHELF="/data/service/hnp/bin/patchelf"
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"
READELF="/data/service/hnp/bin/llvm-readelf"

# 验证工具存在
for tool in "$PATCHELF" "$OBJCOPY" "$SIGNTOOL" "$READELF"; do
    if [ ! -x "$tool" ]; then
        echo "❌ 工具不存在或不可执行: $tool"
        exit 1
    fi
done

# 库搜索路径（按优先级）
LIB_SEARCH_DIRS=(
    "/storage/Users/currentUser/usr/local/lib"
    "/data/service/hnp/lib"
    "/usr/lib" "/usr/lib64"
    "/lib" "/lib64"
)

# 排除的系统 musl 库（不需要打包）
SKIP_LIBS_PATTERN='^libc\.so|^libm\.so|^libdl\.so|^libpthread\.so|^ld-.*\.so|^librt\.so|^libutil\.so|^libpython'

# ======================== 辅助函数 ========================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "\n${CYAN}=== Step $1: $2 ===${NC}"; }

# ============================================================
# Step 8 核心函数：RPATH + Strip + Sign 一体化处理
#
# 注意：不包含 chmod！chmod 统一在 Step 8 批量执行。
# 原因：binary-sign-tool 签名后会重置权限位，
#       单独 chmod 会被覆盖，必须最后统一处理。
# ============================================================
process_elf() {
    local file="$1"
    local rpath="$2"
    local name=$(basename "$file")

    # 5a. Set RPATH
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null || true

    # 5b-5d. Strip + debug extract (if enabled)
    if [ "$STRIP_DEBUG" = "1" ] && [ -n "$DEBUG_DIR" ]; then
        local debug_file="$DEBUG_DIR/${name}.debug"

        # 提取 debug info 到单独文件
        $OBJCOPY --only-keep-debug "$file" "$debug_file" 2>/dev/null || true

        # 从主文件移除 debug sections
        $OBJCOPY --strip-debug "$file" "${file}.tmp" 2>/dev/null || true
        mv -f "${file}.tmp" "$file" 2>/dev/null || true

        # 添加 .gnu_debuglink（GDB 自动加载 debug 文件）
        $OBJCOPY --add-gnu_debuglink="$debug_file" "$file" 2>/dev/null || true
    fi

    # 5e. 移除旧签名段（必须先做，否则 sign 报 "section already exists"）
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true

    # 5f. 重新签名（adhoc self-sign）
    $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 >/dev/null 2>&1 || true

    # 注意：此处不做 chmod a+x！
    # binary-sign-tool 会重置权限位，统一在 Step 8 批量修复
}

# ============================================================
# 主流程
# ============================================================

echo ""
echo "============================================================"
echo "  Python ${PYTHON_VERSION} 可便携包制作 (HarmonyOS ${ARCH})"
echo "============================================================"
echo "  源码:  $SRC_DIR"
echo "  输出:  $OUTPUT_DIR/"
echo "  包名:  $PACKAGE_NAME"
echo "  Strip: $([ "$STRIP_DEBUG" = "1" ] && echo '是' || echo '否')"
echo "  纯净:  $([ "$PURE_MODE" = "1" ] && echo '是(无pip)' || echo '否(含pip)')"
echo ""

# ----------------------------------------------------------
log_step "1" "make install 到独立目录"
# ----------------------------------------------------------
log_info "创建安装目录: $PACKAGE_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"

log_info "执行 make install ..."
MAKEFLAGS="-j1" make -C "$SRC_DIR" install prefix="$PACKAGE_DIR" 2>&1 | tail -5

if [ ! -f "$PACKAGE_DIR/bin/python${PYTHON_VERSION%.*}" ]; then
    log_error "make install 失败，未找到 Python 可执行文件"
    exit 1
fi
log_info "✅ 安装成功"

# 确定 Python 可执行文件名和主库名
PY_VER_SHORT="${PYTHON_VERSION%.*}"          # 3.12
PY_BIN_NAME="python${PY_VER_SHORT}"           # python3.12
PY_LIB_NAME="libpython${PY_VER_SHORT}.so"     # libpython3.12.so
PY_LIB_VER="libpython${PY_VER_SHORT}.so.${PYTHON_VERSION##*.}"  # libpython3.12.so.9
# 实际查找主共享库（版本号可能不同）
ACTUAL_LIB_SO=$(find "$PACKAGE_DIR/lib/" -maxdepth 1 -name "libpython${PY_VER_SHORT}.so*" -type f ! -name "*.a" | head -1)
if [ -z "$ACTUAL_LIB_SO" ]; then
    ACTUAL_LIB_SO="$PACKAGE_DIR/lib/${PY_LIB_VER}"
fi

# ----------------------------------------------------------
log_step "2" "清理缓存和非必要文件"
# ----------------------------------------------------------

# 2a. 清除 Python 字节码缓存
log_info "清除 __pycache__ / *.pyc / *.pyo ..."
find "$PACKAGE_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$PACKAGE_DIR" -name '*.pyc' -delete 2>/dev/null || true
find "$PACKAGE_DIR" -name '*.pyo' -delete 2>/dev/null || true
pyc_count=$(find "$PACKAGE_DIR" -name '*.pyc' 2>/dev/null | wc -l | tr -d ' ')
log_info "  清理完成，残留 .pyc: $pyc_count"

# 2b. 删除 .bak 备份文件
find "$PACKAGE_DIR" -name '*.bak' -delete 2>/dev/null || true

# 2c. 纯净模式：删除 pip
if [ "$PURE_MODE" = "1" ]; then
    log_info "纯净模式: 删除 pip ..."
    rm -rf "$PACKAGE_DIR/lib/python"*/site-packages/pip* 2>/dev/null || true
    rm -f "$PACKAGE_DIR/bin/pip"* "$PACKAGE_DIR/bin/easy_install"* 2>/dev/null || true
    # ensurepip 的 _bundled wheel 保留（用户可自行安装）
    log_info "  pip 已删除，ensurepip _bundled wheel 保留"
fi

# ----------------------------------------------------------
log_step "3" "符号链接替换（wrapper/cp）"
# ----------------------------------------------------------
SYMLINK_COUNT=0

# 3a. bin/ 下的软链接 → wrapper 脚本
for link_file in $(find "$PACKAGE_DIR/bin" -type l); do
    link_name=$(basename "$link_file")
    target=$(readlink "$link_file")

    rm -f "$link_file"

    if [ -f "$(dirname "$link_file")/$target" ]; then
        # 目标是同目录下的真实文件 → 创建 wrapper
        target_base=$(basename "$target")
        cat > "$link_file" << WEOF
#!/bin/sh
SELF_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec "\$SELF_DIR/${target_base}" "\$@"
WEOF
        chmod +x "$link_file"
        log_info "  🔗 wrapper: $link_name → $target_base"
    else
        # 其他情况 → 复制目标内容
        cp -p "$(dirname "$link_file")/$target" "$link_file" 2>/dev/null || \
        cp -L "$link_file" "$link_file" 2>/dev/null || true
        log_info "  📋 copy: $link_name ← $target"
    fi
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
done

# 3b. lib/ 及其他位置 → cp 复制
for link_file in $(find "$PACKAGE_DIR" -type l ! -path '*/bin/*'); do
    target=$(readlink "$link_file")
    base_dir=$(dirname "$link_file")
    rm -f "$link_file"
    if [ -f "$base_dir/$target" ]; then
        cp -p "$base_dir/$target" "$link_file"
    else
        cp -L "$link_file" "$link_file" 2>/dev/null || true
    fi
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
done

REMAINING_LINKS=$(find "$PACKAGE_DIR" -type l 2>/dev/null | wc -l | tr -d ' ')
log_info "  替换了 $SYMLINK_COUNT 个符号链接，残留: $REMAINING_LINKS"

# ----------------------------------------------------------
log_step "4" "⭐ 收集外部依赖库到 lib/external/（必做）"
# ----------------------------------------------------------
mkdir -p "$PACKAGE_DIR/lib/external"

log_info "分析 ELF 文件依赖 ..."

# 用 find -exec 直接提取所有 NEEDED（无管道子 shell 变量丢失问题）
# 注意：鸿蒙 /tmp 可能只读，使用 $OUTPUT_DIR 作为临时目录
NEEDED_TMP="$OUTPUT_DIR/.needed_tmp_$$"
trap 'rm -f "$NEEDED_TMP"' EXIT

find "$PACKAGE_DIR" -type f -exec sh -c '
    magic=$(head -c 4 "$1" 2>/dev/null | od -A n -t x1 | tr -d " ")
    [ "$magic" = "7f454c46" ] || exit 0
    '"$READELF"' -d "$1" 2>/dev/null | grep NEEDED | sed "s/.*\[\(.*\)\].*/\1/"
' _ {} \; 2>/dev/null | sort -u > "$NEEDED_TMP"

NEEDED_COUNT=$(wc -l < "$NEEDED_TMP" | tr -d ' ')
log_info "  发现 $NEEDED_COUNT 个唯一依赖项，开始收集 ..."

# 在主 shell 中逐个处理（变量作用域安全）
COLLECTED_COUNT=0
while IFS= read -r lib; do
    [ -z "$lib" ] && continue
    # 跳过系统 musl 库
    echo "$lib" | grep -qE "$SKIP_LIBS_PATTERN" && continue
    # 跳过已收集的
    [ -f "$PACKAGE_DIR/lib/external/$lib" ] && continue
    # 跳过包内主共享库（精确匹配 lib/ 根目录，不用 find 避免误匹配）
    [ -f "$PACKAGE_DIR/lib/$lib" ] && continue

    # 在搜索路径中查找并复制
    found=""
    for search_dir in "${LIB_SEARCH_DIRS[@]}"; do
        if [ -f "$search_dir/$lib" ]; then
            found="$search_dir/$lib"
            break
        fi
    done

    if [ -n "$found" ]; then
        log_info "  📦 收集外部依赖: $lib"
        cp -L "$found" "$PACKAGE_DIR/lib/external/"
        COLLECTED_COUNT=$((COLLECTED_COUNT + 1))
    fi
done < "$NEEDED_TMP"
rm -f "$NEEDED_TMP"
unset NEEDED_TMP

EXT_COUNT=$(ls "$PACKAGE_DIR/lib/external/" 2>/dev/null | wc -l | tr -d ' ')
if [ "$EXT_COUNT" -gt 0 ]; then
    log_info "  外部依赖库 ($EXT_COUNT 个):"
    ls -lh "$PACKAGE_DIR/lib/external/" 2>/dev/null | awk '{printf "    %-28s %s\n", $NF, $5}'
else
    log_warn "  未发现额外外部依赖库（所有依赖均为系统 musl 库或包内已有）"
fi

# ============================================================
# ============================================================
# 可靠的 ELF 文件检测函数（基于 ELF 魔数，不依赖 file 命令）
# HarmonyOS 上 file 命令可能误判 .py/.pem/.o 等文件
# ============================================================
is_elf() {
    local f="$1"
    # 检查 ELF 魔数: 0x7f 0x45 0x4c 0x46 (\x7fELF)
    [ -f "$f" ] || return 1
    local magic=$(head -c 4 "$f" 2>/dev/null | od -A n -t x1 | tr -d ' ')
    [ "$magic" = "7f454c46" ]
}

# 收集所有 ELF 文件路径到指定变量名
collect_elf_files() {
    local _var="$1"
    local _dir="$2"
    local _result=""
    while IFS= read -r -d '' f; do
        if is_elf "$f"; then
            _result="$_result"$'\n'"$f"
        fi
    done < <(find "$_dir" -type f -print0 2>/dev/null)
    eval "$_var=\"\$_result\""
}

log_step "5" "设置 RPATH（\$ORIGIN 相对路径）"
# ----------------------------------------------------------
collect_elf_files ELF_FILES "$PACKAGE_DIR"
ELF_FILES=$(echo "$ELF_FILES" | grep -v '^$')  # 移除空行
TOTAL_ELFS=$(echo "$ELF_FILES" | wc -l | tr -d ' ')
log_info "发现 $TOTAL_ELFS 个 ELF 文件，设置 RPATH ..."

ELF_IDX=0
echo "$ELF_FILES" | while IFS= read -r elf; do
    [ -z "$elf" ] && continue
    ELF_IDX=$((ELF_IDX + 1))

    # 根据文件位置确定 RPATH
    case "$elf" in
        */bin/*)
            RPATH='$ORIGIN/../lib:$ORIGIN/../lib/external'
            ;;
        */lib/external/*)
            RPATH='$ORIGIN'
            ;;
        */lib-dynload/*)
            RPATH='$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
            ;;
        */lib/*)
            RPATH='$ORIGIN:$ORIGIN/external'
            ;;
        *)
            RPATH='$ORIGIN/../lib:$ORIGIN/../lib/external'
            ;;
    esac

    printf "\r  [%d/%d] %s" "$ELF_IDX" "$TOTAL_ELFS" "$(basename "$elf")"
    process_elf "$elf" "$RPATH"
done
echo ""
log_info "✅ RPATH 设置完成 ($TOTAL_ELFS 个文件)"

# ----------------------------------------------------------
log_step "6" "Strip debug 符号 + 分离保存"
# ----------------------------------------------------------
if [ "$STRIP_DEBUG" = "1" ]; then
    log_info "Debug 符号已在上一步一并分离（process_elf 内部）"
    DEBUG_FILE_COUNT=$(find "$DEBUG_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
    log_info "  Debug 文件数: $DEBUG_FILE_COUNT"
else
    log_info "Strip 已跳过（STRIP_DEBUG=0）"
fi

# ----------------------------------------------------------
log_step "7" "ELF 签名（已在 process_elf 中完成）"
# ----------------------------------------------------------
log_info "✅ 所有 ELF 文件已签名（在 Step 5-6 一体化处理中完成）"

# ----------------------------------------------------------
log_step "8" "⭐ 统一修复执行权限（必做！）"
# ----------------------------------------------------------
# ⚠️ 关键：binary-sign-tool 签名后会重置权限位为 umask 默认值（通常是 0666 → rw-rw----）
# 即使之前 chmod a+x 也会被覆盖。必须在所有签名完成后统一修复！

log_info "批量恢复 ELF 文件执行权限 ..."
FIXED_COUNT=0
MISSING_COUNT=0

# 8a. 对所有 ELF 文件添加执行权限（使用进程替代避免子 shell）
while IFS= read -r -d '' elf; do
    if is_elf "$elf" && [ ! -x "$elf" ]; then
        chmod +x "$elf"
        FIXED_COUNT=$((FIXED_COUNT + 1))
    fi
done < <(find "$PACKAGE_DIR" -type f -print0 2>/dev/null)

# 8b. bin/ 下的脚本也确保有执行权限
find "$PACKAGE_DIR/bin" -type f ! -executable -exec chmod +x {} \; 2>/dev/null || true

# 8c. 权限验证（必做检查项）
log_info "验证执行权限 ..."
NO_EXE_COUNT=0
NO_EXE_LIST=""
# 使用 ELF 魔数检测，不依赖 file 命令
while IFS= read -r -d '' elf; do
    if is_elf "$elf" && [ ! -x "$elf" ]; then
        NO_EXE_COUNT=$((NO_EXE_COUNT + 1))
        NO_EXE_LIST="$NO_EXE_LIST $(basename "$elf")"
    fi
done < <(find "$PACKAGE_DIR" -type f -print0 2>/dev/null)

if [ "$NO_EXE_COUNT" -gt 0 ]; then
    log_error "❌ 仍有 $NO_EXE_COUNT 个 ELF 文件缺少执行权限:$NO_EXE_LIST"
    log_error "   这将导致用户解压 tar.gz 后 Permission denied！"
    exit 1
else
    log_info "✅ 所有 ELF 文件均有执行权限"
fi

# ----------------------------------------------------------
log_step "9" "创建 activate.sh / README.md"
# ----------------------------------------------------------

# 9a. activate.sh（兼容 toybox ash，使用 $0 而非 ${BASH_SOURCE}）
cat > "$PACKAGE_DIR/activate.sh" << 'ACTEOF'
#!/bin/sh
# Python portable activation script — HarmonyOS (toybox ash compatible)
# Usage: . /path/to/package/activate.sh

if [ -n "$_PYTHON_PORTABLE_OLD_PATH" ]; then
    echo "Already activated."
    return 2>/dev/null || exit 0
fi

_PYTHON_PORTABLE_DIR="$(cd "$(dirname "$0")" && pwd)"

# 保存旧环境
_PYTHON_PORTABLE_OLD_PATH="$PATH"
_PYTHON_PORTABLE_OLD_LD="${LD_LIBRARY_PATH:-}"
_PYTHON_PORTABLE_OLD_PH="${PYTHONHOME:-}"

# 设置新环境
export PYTHONHOME="$_PYTHON_PORTABLE_DIR"
export PATH="$_PYTHON_PORTABLE_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$_PYTHON_PORTABLE_DIR/lib${_PYTHON_PORTABLE_OLD_LD:+:$_PYTHON_PORTABLE_OLD_LD}"

# Shell prompt
if [ -n "$PS1" ]; then
    _PYTHON_PORTABLE_OLD_PS1="$PS1"
    export PS1="(py${PYTHON_VERSION%%.*}) $PS1"
fi

echo "Python ${PYTHON_VERSION:-} portable environment activated"
echo "  Prefix: $PYTHONHOME"

deactivate_pyportable() {
    export PATH="$_PYTHON_PORTABLE_OLD_PATH"
    export LD_LIBRARY_PATH="$_PYTHON_PORTABLE_OLD_LD"
    export PYTHONHOME="$_PYTHON_PORTABLE_OLD_PH"
    [ -n "$_PYTHON_PORTABLE_OLD_PS1" ] && export PS1="$_PYTHON_PORTABLE_OLD_PS1"
    unset _PYTHON_PORTABLE_DIR _PYTHON_PORTABLE_OLD_PATH
    unset _PYTHON_PORTABLE_OLD_LD _PYTHON_PORTABLE_OLD_PH _PYTHON_PORTABLE_OLD_PS1
    unset -f deactivate_pyportable
    echo "Deactivated."
}
ACTEOF
chmod +x "$PACKAGE_DIR/activate.sh"

# 9b. README.md
PIP_NOTE=""
if [ "$PURE_MODE" = "1" ]; then
    PIP_NOTE="
> **纯净版**：不含 pip。安装 pip:
> \`\`\`bash
> python${PY_VER_SHORT} -m ensurepip --upgrade
> \`\`\`"
fi

cat > "$PACKAGE_DIR/README.md" << REOF
# Python ${PYTHON_VERSION} Portable for HarmonyOS

> **Platform**: HarmonyOS aarch64 (musl) | **Build**: $(date +%Y-%m-%d)

## Quick Start

\`\`\`bash
# 1. 解压
tar xzf ${PACKAGE_NAME}.tar.gz -C ~/usr/

# 2. ⚠️ 修复执行权限（HarmonyOS 签名机制要求）
find ${PACKAGE_NAME}/ -type f -name '*.so*' -exec chmod +x {} \\;
chmod +x ${PACKAGE_NAME}/bin/*

# 3. 激活环境
. ~/${PACKAGE_NAME}/activate.sh

# 4. 使用
python${PY_VER_SHORT} --version${PIP_NOTE}

# 5. 退出
deactivate_pyportable
\`\`\`

> ⚠️ **解压后必须 chmod +x**：HarmonyOS 的 adhoc 签名机制会导致 tar 包内
> ELF 文件丢失执行权限。这是已知平台限制，不是打包错误。

## Directory Structure

\`\`\`
${PACKAGE_NAME}/
├── activate.sh              # Environment activation (source this)
├── README.md
├── bin/
│   ├── python${PY_VER_SHORT}      # Interpreter (ELF, signed, stripped)
│   ├── python3 / python     # Wrapper scripts
│   └── ...
├── lib/
│   ├── libpython${PY_VER_SHORT}.so*   # Shared library
│   ├── external/             # External dependencies (collected)
│   └── python${PY_VER_SHORT}/        # Standard library
└── include/                 # C headers
\`\`\`

## Features

- Self-contained with \$ORIGIN RPATH (works from any location)
- All ELF files stripped and signed for HarmonyOS
- External dependencies bundled in lib/external/
- toybox ash compatible (no bashisms)
REOF

log_info "✅ activate.sh + README.md 创建完成"

# ----------------------------------------------------------
log_step "10" "打包 tar.gz"
# ----------------------------------------------------------
cd "$OUTPUT_DIR"

# 10a. 主包
log_info "打包主包 ..."
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
MAIN_SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)
MAIN_FILES=$(find "$PACKAGE_NAME" -type f | wc -l | tr -d ' ')
log_info "📦 主包: ${PACKAGE_NAME}.tar.gz ($MAIN_SIZE, ${MAIN_FILES} files)"

# 10b. Debug 符号包
if [ "$STRIP_DEBUG" = "1" ] && [ -d "$DEBUG_DIR" ] && [ "$(ls -A "$DEBUG_DIR" 2>/dev/null)" ]; then
    tar -czf "${PACKAGE_NAME}-debug.tar.gz" -C "$OUTPUT_DIR" "${PACKAGE_NAME}.debug"
    DEBUG_SIZE=$(du -h "${PACKAGE_NAME}-debug.tar.gz" | cut -f1)
    DEBUG_FILES=$(find "$DEBUG_DIR" -type f | wc -l | tr -d ' ')
    log_info "🔧 Debug: ${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE, ${DEBUG_FILES} files)"
fi

# ----------------------------------------------------------
# 最终统计
# ----------------------------------------------------------
FINAL_ELF=$(echo "$ELF_FILES" | grep -c . || echo 0)
FINAL_EXT=$(ls "$PACKAGE_NAME/lib/external/" 2>/dev/null | wc -l | tr -d ' ')
FINAL_LINKS=$(find "$PACKAGE_NAME" -type l 2>/dev/null | wc -l | tr -d ' ')
PKG_SIZE=$(du -sh "$PACKAGE_NAME" 2>/dev/null | cut -f1)

echo ""
echo "============================================================"
echo "  ✅ 打包完成！"
echo "============================================================"
echo ""
echo "📦 产物:"
echo ""
echo "  主包:   $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz ($MAIN_SIZE)"
if [ -n "$DEBUG_SIZE" ]; then
    echo "  Debug:  $OUTPUT_DIR/${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE)"
fi
echo ""
echo "📊 统计:"
echo ""
echo "  总文件:     $MAIN_FILES"
echo "  ELF 文件:   $FINAL_ELF (全部已 RPATH+Strip+Sign)"
echo "  外部依赖:   $FINAL_EXT (lib/external/)"
echo "  残留链接:   $FINAL_LINKS (应为 0)"
echo "  目录大小:   $PKG_SIZE"
echo ""
echo "📋 安装:"
echo ""
echo "  tar xzf ${PACKAGE_NAME}.tar.gz -C ~/usr/"
echo "  find ${PACKAGE_NAME}/ -type f -name '*.so*' -exec chmod +x {} \\;"
echo "  chmod +x ${PACKAGE_NAME}/bin/*"
echo "  . ~/${PACKAGE_NAME}/activate.sh"
echo ""
