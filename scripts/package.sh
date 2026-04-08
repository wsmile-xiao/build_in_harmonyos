#!/bin/env zsh
# ==============================================================================
# [Layer L1.5] package.sh — 预编译包一键打包工具
# ==============================================================================
# 层级: L1.5 (半自动, 大部分步骤自动)
# 决策点: 极少 (仅签名失败和 RPATH 策略需人工确认)
# 入口: ./scripts/package.sh <software_name> <version> [--static] [--debug] [--skip-sign]
# 依赖: llvm-objcopy, llvm-readelf, binary-sign-tool, patchelf(可选), strip
# 调用者: AI 在 verify-build PASS 后调用; 或手动执行
# 基于: knowledge/packaging.md v2.3
# ==============================================================================

set -euo pipefail

# ============ 全局路径配置 ============
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ARCHIVES_DIR="${PROJECT_DIR}/archives"
KNOWLEDGE_DIR="${PROJECT_DIR}/knowledge"
HNP_BIN="/data/service/hnp/bin"

# 工具路径（优先从 HNP_BIN 查找，再回退到 PATH）
LLVM_OBJCOPY="${LLVM_OBJCOPY:-${HNP_BIN}/llvm-objcopy}"
LLVM_READELF="${LLVM_READELF:-${HNP_BIN}/llvm-readelf}"
BINARY_SIGN_TOOL="${BINARY_SIGN_TOOL:-${HNP_BIN}/binary-sign-tool}"
PATCHELF="${PATCHELF:-patchelf}"

# 默认值
SOFTWARE_NAME=""
VERSION=""
STATIC_BUILD=false
DEBUG_BUILD=true   # debug 包默认启用（SKILL §6.1 必填文件要求）
SKIP_SIGN=false
# DEFAULT_PREFIX: 唯一权威的安装前缀变量（由 init-build.sh export 或环境变量传入）
# --prefix 参数可覆盖，否则通过 fallback 自动检测
# 注意：v4.3+ 优先使用 $TEST_PREFIX（staging 目录）作为打包来源
DEFAULT_PREFIX="${DEFAULT_PREFIX:-}"
TEST_PREFIX="${TEST_PREFIX:-}"

# ============ 帮助信息 ============
show_help() {
    cat <<'EOF'
用法: ./scripts/package.sh <软件名> <版本> [选项]

参数:
  <软件名>     软件名称 (如 sed, coreutils, python)
  <版本>       版本号 (如 4.9, 3.9.25)

选项:
  --static     启用静态库打包模式 (--without-shared 场景)
                - Step 3 跳过 .so 符号链接替换
                - Step 4 仅收集动态依赖
                - Step 5 RPATH 只处理可执行文件
                - Step 6 .a 文件跳过 strip
  --debug      同时生成 debug 包 (含调试符号, .debug 文件)
  --skip-sign  跳过 ELF 签名步骤 (Step 7)
  --prefix=PATH  指定安装前缀路径 (默认自动检测)
  -h, --help   显示此帮助

示例:
  ./scripts/package.sh sed 4.9
  ./scripts/package.sh openssl 3.0.13 --static --debug
  ./scripts/package.sh python 3.9.25 --skip-sign
  ./scripts/package.sh ncurses 6.4 --static --prefix=$HOME/usr/local

输出位置:
  archives/{首字母}/{软件名}/{版本}/packaging/
    ├── {name}-{ver}-ohos-aarch64.tar.gz      主包
    ├── {name}-{ver}-ohos-aarch64-debug.tar.gz debug包(--debug时)
    └── install-{name}-{ver}.sh                 安装脚本

基于 packaging.md v2.3 的 10 步标准化流程。
EOF
}

# ============ 参数解析 ============
while [ $# -gt 0 ]; do
    case "$1" in
        --static)     STATIC_BUILD=true ;;
        --debug)      DEBUG_BUILD=true ;;
        --no-debug)   DEBUG_BUILD=false ;;
        --skip-sign)  SKIP_SIGN=true ;;
        --prefix=*)   DEFAULT_PREFIX="${1#--prefix=}" ;;
        -h|--help)    show_help; exit 0 ;;
        -*)
            echo "未知选项: $1"
            echo "使用 -h 查看帮助"
            exit 1
            ;;
        *)
            if [ -z "$SOFTWARE_NAME" ]; then
                SOFTWARE_NAME="$1"
            elif [ -z "$VERSION" ]; then
                VERSION="$1"
            else
                echo "多余参数: $1"
                exit 1
            fi
            ;;
    esac
    shift
done

# 必需参数校验
if [ -z "$SOFTWARE_NAME" ] || [ -z "$VERSION" ]; then
    echo "错误: 缺少必需参数 <软件名> 和 <版本>"
    echo ""
    show_help
    exit 1
fi

# ============ 确定归档目录和打包工作目录 ============
FIRST_LETTER=$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')
ARCHIVE_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}"
PACKAGING_DIR="${ARCHIVE_DIR}/packaging"
PKGDIR="${PACKAGING_DIR}/pkg-${SOFTWARE_NAME}-${VERSION}"
DEBUG_DIR="${PACKAGING_DIR}/debug-symbols"

# 打印配置摘要
echo "============================================"
echo "  Package: ${SOFTWARE_NAME} ${VERSION}"
echo "  Archive: ${ARCHIVE_DIR}"
echo "  PkgDir : ${PKGDIR}"
echo "  Static : $([ "$STATIC_BUILD" = true ] && echo 'YES' || echo 'NO')"
echo "  Debug  : $([ "$DEBUG_BUILD" = true ] && echo 'YES' || echo 'NO')"
echo "  Sign   : $([ "$SKIP_SIGN" = true ] && echo 'SKIP' || echo 'YES')"
echo "============================================"

# ============ 前置检查 ============
# 检查归档目录存在
if [ ! -d "$ARCHIVE_DIR" ]; then
    echo "ERROR: 归档目录不存在: $ARCHIVE_DIR"
    echo "  请先运行 finish-build.sh + finalize-archive.sh 创建归档结构"
    exit 1
fi

# $DEFAULT_PREFIX 自动检测逻辑
if [ -z "$DEFAULT_PREFIX" ]; then
    # 策略1: 环境变量 DEFAULT_PREFIX
    DEFAULT_PREFIX="${DEFAULT_PREFIX:-}"

    # 策略2: 常见默认路径
    if [ -z "$DEFAULT_PREFIX" ] || [ ! -d "$DEFAULT_PREFIX" ]; then
        for _try_prefix in "$HOME/usr/local" "/storage/Users/currentUser/usr/local" "$HOME/.local"; do
            if [ -d "$_try_prefix/bin" ] || [ -d "$_try_prefix/lib" ]; then
                DEFAULT_PREFIX="$_try_prefix"
                break
            fi
        done
    fi

    # 策略3: 从 manifest.yaml 提取 install_prefix
    if [ -z "$DEFAULT_PREFIX" ] || [ ! -d "$DEFAULT_PREFIX" ]; then
        if [ -f "${ARCHIVE_DIR}/manifest.yaml" ]; then
            _manifest_prefix=$(grep '^install_prefix:' "${ARCHIVE_DIR}/manifest.yaml" 2>/dev/null | head -1 | sed 's/install_prefix:[[:space:]]*//' | sed "s/[\"']//g")
            if [ -n "$_manifest_prefix" ]; then
                DEFAULT_PREFIX="$_manifest_prefix"
            fi
        fi
    fi

    # 策略4: 从 build log 或 session 文件推断 (可选增强)
    if [ -z "$DEFAULT_PREFIX" ] || [ ! -d "$DEFAULT_PREFIX" ]; then
        # 尝试从最近的 build session 查找
        for _session_file in \
            "${ARCHIVE_DIR}/build-session.env" \
            "${PROJECT_DIR}/.build-session.env" \
            "${HOME}/.last-build-prefix"; do
            if [ -f "$_session_file" ]; then
                _sp=$(grep -E '^PREFIX=|^INSTALL_PREFIX=|^prefix=' "$_session_file" 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[\"']//g")
                if [ -n "$_sp" ] && [ -d "$_sp" ]; then
                    DEFAULT_PREFIX="$_sp"
                    break
                fi
            fi
        done
    fi
fi

if [ -z "$DEFAULT_PREFIX" ]; then
    echo "WARNING: 无法自动检测 \$DEFAULT_PREFIX，将尝试从常见路径复制"
    echo "  可通过 --prefix=PATH 显式指定"
    DEFAULT_PREFIX="$HOME/usr/local"
fi

echo "  Prefix : ${DEFAULT_PREFIX}"
echo ""

# ================================================================
# Step 1: 安装到独立目录 / 创建打包工作目录
# ================================================================
# packaging.md Step 1: 使用独立前缀，确保纯净
# 本脚本假设 make install 已完成，此处从 $DEFAULT_PREFIX 复制到 PKGDIR
#
echo "[Step 1/10] 创建打包工作目录..."
rm -rf "$PKGDIR"
mkdir -p "${PKGDIR}/bin"
mkdir -p "${PKGDIR}/lib"
mkdir -p "${PKGDIR}/lib/external"
mkdir -p "${PKGDIR}/include"
mkdir -p "${PKGDIR}/share"
mkdir -p "${PKGDIR}/doc"
echo "  OK: ${PKGDIR} created"

# ================================================================
# Step 2: 清理缓存和非必要文件
# ================================================================
# packaging.md Step 2:
#   2a. Python 字节码缓存 (__pycache__ / *.pyc / *.pyo)
#   2b. .bak 备份文件
#   2c. pip/easy_install 等非标准库内容
#   2d. (可选) 测试套件
# 注意: 此步在复制后执行，清理 PKGDIR 内的缓存文件
#
echo "[Step 2/10] 清理缓存和非必要文件..."

# 2a. Python 字节码缓存
find "$PKGDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$PKGDIR" -name '*.pyc' -delete 2>/dev/null || true
find "$PKGDIR" -name '*.pyo' -delete 2>/dev/null || true

# 2b. .bak 备份文件
find "$PKGDIR" -name '*.bak' -delete 2>/dev/null || true

# 2c. pip / easy_install 非标准库内容
rm -rf "$PKGDIR"/lib/python*/site-packages/pip* 2>/dev/null || true
rm -f "$PKGDIR"/bin/pip* "$PKGDIR"/bin/easy_install* 2>/dev/null || true

# 2d. LaTex / info 等大体积非必要文件 (可选清理)
find "$PKGDIR" -name '*.info' -delete 2>/dev/null || true
find "$PKGDIR" -name '*.info-*' -delete 2>/dev/null || true

echo "  OK: cache cleaned"

# ================================================================

# Step 2b: 从 staging 目录 复制文件到 PKGDIR
# ================================================================
# v4.3+: 优先从 $TEST_PREFIX（staging 目录）复制
# fallback 到 $DEFAULT_PREFIX（兼容旧流程）
#
echo "[Step 2b/10] 从安装目录复制文件..."

# 确定源目录：优先 TEST_PREFIX
_SRC_PREFIX="$TEST_PREFIX"
if [ -z "$_SRC_PREFIX" ] || [ ! -d "$_SRC_PREFIX/bin" ]; then
    _SRC_PREFIX="$DEFAULT_PREFIX"
fi

if [ -z "$_SRC_PREFIX" ] || [ ! -d "$_SRC_PREFIX" ]; then
    echo "  ERROR: 无法找到安装目录 (\$TEST_PREFIX=$TEST_PREFIX, \$DEFAULT_PREFIX=$DEFAULT_PREFIX)"
    exit 1
fi

echo "  源目录: $_SRC_PREFIX"

_copy_count=0
copy_dir_safe() {
    _src="$1"
    _dst="$2"
    if [ -d "$_src" ]; then
        cp -a "$_src"/* "$_dst/" 2>/dev/null || true
        _cnt=$(find "$_dst" -type f 2>/dev/null | wc -l | tr -d ' ')
        _copy_count=$((_copy_count + _cnt))
    fi
}

copy_dir_safe "$_SRC_PREFIX/bin"     "${PKGDIR}/bin"
copy_dir_safe "$_SRC_PREFIX/lib"     "${PKGDIR}/lib"
copy_dir_safe "$_SRC_PREFIX/include" "${PKGDIR}/include"
copy_dir_safe "$_SRC_PREFIX/share"   "${PKGDIR}/share"

_bin_count=$(find "${PKGDIR}/bin" -type f 2>/dev/null | wc -l | tr -d ' ')
_lib_count=$(find "${PKGDIR}/lib" -type f 2>/dev/null | wc -l | tr -d ' ')
echo "  OK: $_bin_count binaries, $_lib_count library files copied"


# Step 2e: 应用 EXCLUDE_LIST（打包排除列表）
# ================================================================
# 排除编译通过但有问题的命令/库（平台限制无法规避）
# 排除列表位置（按优先级）:
#   1. archives/{name}/{version}/EXCLUDE_LIST   (版本级)
#   2. archives/{name}/EXCLUDE_LIST              (软件级)
# 格式: 每行一个文件名（bin/ 或 lib/ 下的 basename）
#       # 开头为注释
#
_EXCLUDE_FILE=""
if [ -f "${ARCHIVE_DIR}/EXCLUDE_LIST" ]; then
    _EXCLUDE_FILE="${ARCHIVE_DIR}/EXCLUDE_LIST"
elif [ -f "${ARCHIVE_DIR}/../EXCLUDE_LIST" ]; then
    _EXCLUDE_FILE="${ARCHIVE_DIR}/../EXCLUDE_LIST"
fi

if [ -n "$_EXCLUDE_FILE" ]; then
    echo "[Step 2e/10] 应用排除列表: $(basename "$_EXCLUDE_FILE")"
    _EXCLUDED=0
    while IFS= read -r _line || [ -n "$_line" ]; do
        # 跳过空行和注释
        case "$_line" in \#*|"") continue ;; esac
        _target=$(echo "$_line" | sed 's/[[:space:]]*$//')  # trim
        [ -z "$_target" ] && continue

        # 在 PKGDIR 的 bin/ lib/ 中查找并删除
        for _loc in bin lib; do
            if [ -f "${PKGDIR}/${_loc}/${_target}" ]; then
                rm -f "${PKGDIR}/${_loc}/${_target}"
                _EXCLUDED=$((_EXCLUDED + 1))
                echo "    excluded: ${_loc}/${_target}"
            fi
        done
    done < "$_EXCLUDE_FILE"
    echo "  OK: $_EXCLUDED files excluded"
else
    echo "[Step 2e/10] 无排除列表，跳过"
fi

# ================================================================
# Step 3: 符号链接替换
# ================================================================
# packaging.md Step 3: 鸿蒙 SELinux 限制软链接
#   3a. bin/ 下可执行别名 -> wrapper 脚本
#   3b. lib/ 下共享库别名 -> cp 复制
#   3c. 其他位置 (pkgconfig/man 等) -> cp 复制
# 静态模式 (--static): 跳过 .so 相关的符号链接处理
#
echo "[Step 3/10] 解析并替换软链接..."
_link_count=0

# 3a. bin/ 下的可执行文件别名 -> wrapper 脚本
for _link in $(find "${PKGDIR}/bin" -type l 2>/dev/null); do
    _target=$(readlink "$_link")
    if [ -n "$_target" ]; then
        _link_name=$(basename "$_link")
        _target_name=$(basename "$_target")
        rm -f "$_link"
        # 生成 wrapper 脚本
        cat > "$_link" <<WRAPPER_EOF
#!/bin/sh
SELF_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec "\$SELF_DIR/${_target_name}" "\$@"
WRAPPER_EOF
        chmod +x "$_link"
        _link_count=$((_link_count + 1))
    fi
done

# 3b. lib/ 下的共享库别名 -> cp 复制 (静态模式下跳过)
if [ "$STATIC_BUILD" != true ]; then
    find "${PKGDIR}/lib" -type l ! -path '*/lib-dynload/*' 2>/dev/null | while read -r _symlink; do
        _target=$(readlink "$_symlink")
        if [ -n "$_target" ]; then
            _symlink_dir=$(dirname "$_symlink")
            rm -f "$_symlink"
            if [ -f "${_symlink_dir}/${_target}" ]; then
                cp -p "${_symlink_dir}/${_target}" "$_symlink" 2>/dev/null || true
            fi
            _link_count=$((_link_count + 1))
        fi
    done
fi

# 3c. pkgconfig/man 等其他位置的软链接 -> cp 复制
find "$PKGDIR" -type l 2>/dev/null | while read -r _link; do
    _target=$(readlink "$_link")
    if [ -n "$_target" ]; then
        _link_dir=$(dirname "$_link")
        rm -f "$_link"
        if [ -f "${_link_dir}/${_target}" ]; then
            cp -p "${_link_dir}/${_target}" "$_link" 2>/dev/null || true
        fi
    fi
done

# 验证: 检查残留符号链接
_remaining_links=$(find "$PKGDIR" -type l 2>/dev/null | wc -l | tr -d ' ')
echo "  OK: symlinks replaced (${_remaining_links} remaining)"

# ================================================================
# Step 4: 收集外部依赖库到 lib/external/
# ================================================================
# packaging.md Step 4: 最关键的一步
#   - 使用 llvm-readelf -d 分析 NEEDED 库
#   - 排除系统 musl 库 (libc, libm, libdl, libpthread 等)
#   - 递归分析依赖的依赖 (depth < 2 防循环)
#   - 放入 lib/external/
# 静态模式: 已静态链接的库不会出现在 NEEDED 中，自然跳过
#
echo "[Step 4/10] 收集外部依赖共享库..."

# 排除的系统 musl 库
SKIP_LIBS_PATTERN='^libc\.so|^libm\.so|^libdl\.so|^libpthread\.so|^ld-.*\.so|^librt\.so|^libutil\.so|^libpython'

# 搜索路径 (按优先级)
LIB_SEARCH_DIRS=""
for _sd in \
    "${_SRC_PREFIX:-$TEST_PREFIX}/lib" \
    "${DEFAULT_PREFIX}/lib" \
    "/storage/Users/currentUser/usr/local/lib" \
    "${HNP_BIN}/../lib" \
    "/data/service/hnp/lib" \
    "/usr/lib" "/usr/lib64" "/lib" "/lib64"; do
    if [ -d "$_sd" ]; then
        LIB_SEARCH_DIRS="${LIB_SEARCH_DIRS}${_sd}
"
    fi
done

DEPS_COLLECTED=0
DEBUG_COLLECT=""

# collect_deps 函数: 递归收集单个 ELF 的外部依赖
# 参数: $1=elf文件, $2=当前深度
collect_deps() {
    _elf="$1"
    _depth="${2:-0}"

    # 使用 ldd 或 llvm-readelf 分析依赖
    if [ -x "$LLVM_READELF" ]; then
        _needed=$("$LLVM_READELF" -d "$_elf" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/')
    else
        # 回退到 ldd
        _needed=$(ldd "$_elf" 2>/dev/null | grep '=>' | awk '{print $1}')
    fi

    for _lib in $_needed; do
        # 跳过系统 musl 库
        echo "$_lib" | grep -qE "$SKIP_LIBS_PATTERN" && continue

        # 跳过已收集的
        [ -f "${PKGDIR}/lib/external/${_lib}" ] && continue

        # 跳过包内已有的
        [ -f "${PKGDIR}/lib/${_lib}" ] && continue
        find "${PKGDIR}/lib" -name "${_lib}" -type f >/dev/null 2>&1 && continue

        # 在搜索路径中查找
        _found=""
        _save_ifs="$IFS"
        IFS='
'
        for _search_dir in $LIB_SEARCH_DIRS; do
            IFS="$_save_ifs"
            [ -z "$_search_dir" ] && continue
            if [ -f "${_search_dir}/${_lib}" ]; then
                _found="${_search_dir}/${_lib}"
                break
            fi
        done
        IFS="$_save_ifs"

        if [ -n "$_found" ] && [ -f "$_found" ]; then
            cp -L "$_found" "${PKGDIR}/lib/external/" 2>/dev/null
            DEPS_COLLECTED=$((DEPS_COLLECTED + 1))
            DEBUG_COLLECT="${DEBUG_COLLECT}  collected: ${_lib}
"

            # 递归分析该依赖自身的依赖 (depth < 2)
            if [ "$_depth" -lt 2 ]; then
                collect_deps "${PKGDIR}/lib/external/${_lib}" $((_depth + 1))
            fi
        fi
    done
}

# 对所有 ELF 文件执行依赖收集
# zsh glob qualifier: **/*(.) 只匹配普通文件, 比 find|file|grep 管道快 100x
_ELF_COUNT=0
for _elf in ${PKGDIR}/bin/**/*(.N) ${PKGDIR}/lib/**/*(.N); do
    [[ "$(head -c 4 $_elf 2>/dev/null)" == '\x7fELF' ]] || continue
    collect_deps "$_elf" 0
    _ELF_COUNT=$(( _ELF_COUNT + 1 ))
done
# ================================================================
# Step 5: 设置 RPATH ($ORIGIN 相对路径)
# ================================================================
# packaging.md Step 5 RPATH 规则表:
#   bin/ 可执行文件      -> $ORIGIN/../lib:$ORIGIN/../lib/external
#   lib/ 主共享库         -> $ORIGIN:$ORIGIN/external
#   lib-dynload/*.so      -> $ORIGIN:$ORIGIN/..:$ORIGIN/../external
#   lib/external/*        -> $ORIGIN
# 静态模式: 只处理可执行文件
#
echo "[Step 5/10] 设置 RPATH (\$ORIGIN-based)..."

RPATH_SET=0
set_rpath_for_file() {
    _file="$1"
    _rpath="$2"

    if command -v "$PATCHELF" >/dev/null 2>&1; then
        if "$PATCHELF" --set-rpath "$_rpath" "$_file" 2>/dev/null; then
            RPATH_SET=$((RPATH_SET + 1))
        fi
    else
        # 回退: chrpath (只支持缩短 RPATH，不支持设置 $ORIGIN)
        chrpath -r "$_rpath" "$_file" 2>/dev/null || true
    fi
}

# 5a. bin/ 下可执行文件
_RPATH_BIN='$ORIGIN/../lib:$ORIGIN/../lib/external'
for _elf in $(find "${PKGDIR}/bin" -type f -exec file {} \; 2>/dev/null | grep -E ': ELF.*(executable|shared object)' | cut -d: -f1); do
    set_rpath_for_file "$_elf" "$_RPATH_BIN"
done

# 5b. lib/ 下主共享库 (静态模式跳过)
if [ "$STATIC_BUILD" != true ]; then
    _RPATH_LIB='$ORIGIN:$ORIGIN/external'
    for _elf in $(find "${PKGDIR}/lib" -maxdepth 1 -name '*.so*' -type f 2>/dev/null); do
        set_rpath_for_file "$_elf" "$_RPATH_LIB"
    done

    # 5c. 扩展模块 (lib-dynload)
    _RPATH_DYNLOAD='$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
    find "$PKGDIR" -path '*/lib-dynload/*.so' -type f 2>/dev/null | while read -r _so; do
        set_rpath_for_file "$_so" "$_RPATH_DYNLOAD"
    done
fi

# 5d. 外部依赖库
_RPATH_EXT='$ORIGIN'
find "${PKGDIR}/lib/external" -type f 2>/dev/null | while read -r _ext; do
    set_rpath_for_file "$_ext" "$_RPATH_EXT"
done

echo "  OK: RPATH set on $RPATH_SET files"

# ================================================================
# Step 6: Strip Debug 符号 + 分离保存
# ================================================================
# packaging.md Step 6:
#   - llvm-objcopy --only-keep-debug  提取 debug 信息
#   - llvm-objcopy --strip-debug       移除 debug sections
#   - llvm-objcopy --add-gnu_debuglink 添加 debug link
#   --debug 模式: 保留 .debug 文件并单独打包
#   静态模式: .a 文件跳过 (已 stripped)
#
echo "[Step 6/10] Strip 调试符号..."

STRIP_COUNT=0
DEBUG_COUNT=0

if [ "$DEBUG_BUILD" = true ]; then
    rm -rf "$DEBUG_DIR"
    mkdir -p "$DEBUG_DIR"
fi

strip_debug_single() {
    _file="$1"
    _name=$(basename "$_file")

    # .a 静态库跳过
    case "$_name" in
        *.a) return 0 ;;
    esac

    if [ -x "$LLVM_OBJCOPY" ]; then
        if [ "$DEBUG_BUILD" = true ]; then
            # 提取 debug 信息
            "$LLVM_OBJCOPY" --only-keep-debug "$_file" "${DEBUG_DIR}/${_name}.debug" 2>/dev/null && \
                DEBUG_COUNT=$((DEBUG_COUNT + 1))

            # 移除 debug sections
            "$LLVM_OBJCOPY" --strip-debug "$_file" "${_file}.tmp" 2>/dev/null && \
                mv -f "${_file}.tmp" "$_file" 2>/dev/null

            # 添加 gnu_debuglink
            "$LLVM_OBJCOPY" --add-gnu_debuglink="${DEBUG_DIR}/${_name}.debug" "$_file" 2>/dev/null || true
        else
            # 非 debug 模式: 直接 strip
            "$LLVM_OBJCOPY" --strip-debug "$_file" "${_file}.tmp" 2>/dev/null && \
                mv -f "${_file}.tmp" "$_file" 2>/dev/null
        fi
        STRIP_COUNT=$((STRIP_COUNT + 1))
    else
        # 回退到系统 strip
        strip "$_file" 2>/dev/null || true
        STRIP_COUNT=$((STRIP_COUNT + 1))
    fi
}

# 对所有 ELF 文件执行 strip
for _elf in $(find "${PKGDIR}/bin" "${PKGDIR}/lib" -type f -exec file {} \; 2>/dev/null | grep -E ': ELF' | cut -d: -f1); do
    strip_debug_single "$_elf"
done

# 也处理 lib/external 中的 ELF
find "${PKGDIR}/lib/external" -type f -exec file {} \; 2>/dev/null | grep -E ': ELF' | cut -d: -f1 | while read -r _e; do
    strip_debug_single "$_e"
done

echo "  OK: stripped $STRIP_COUNT files${DEBUG_BUILD:+, separated $DEBUG_COUNT debug symbols}"

# ================================================================
# Step 7: ELF 签名 (adhoc self-sign)
# ================================================================
# packaging.md Step 7:
#   - 先 llvm-objcopy --remove-section .codesign 移除旧签名
#   - binary-sign-tool sign -inFile -outFile -selfSign 1
#   - 最多重试 3 次
#   - 失败标记为 .unsigned 但不中断流程
#   - --skip-sign 完全跳过此步
#
echo "[Step 7/10] ELF 签名..."
SIGN_OK=0
SIGN_FAIL=0
SIGN_SKIP=0

if [ "$SKIP_SIGN" = true ]; then
    echo "  SKIP: signing disabled (--skip-sign)"
    SIGN_SKIP=$(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -ci 'ELF' || echo "0")

elif [ -x "$BINARY_SIGN_TOOL" ]; then

    sign_elf_single() {
        _file="$1"
        _max_retries=3
        _retry=0
        _sign_result=1

        # 移除旧签名段 (必须先做，否则 sign 报错 "section already exists")
        if [ -x "$LLVM_OBJCOPY" ]; then
            "$LLVM_OBJCOPY" --remove-section .codesign "$_file" 2>/dev/null || true
        fi

        while [ "$_retry" -lt "$_max_retries" ]; do
            _retry=$((_retry + 1))
            if "$BINARY_SIGN_TOOL" sign -inFile "$_file" -outFile "$_file" -selfSign 1 2>/dev/null; then
                _sign_result=0
                break
            fi
            sleep 1
        done

        if [ "$_sign_result" -ne 0 ]; then
            # 所有重试失败 -> 标记为 .unsigned
            touch "${_file}.unsigned" 2>/dev/null || true
            echo "    WARN: signing failed after retries: $(basename "$_file")"
        fi
        return $_sign_result
    }

    # 批量签名所有 ELF 文件
    for _elf in $(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -E ': ELF.*(executable|shared|relocatable)' | cut -d: -f1); do
        if sign_elf_single "$_elf"; then
            SIGN_OK=$((SIGN_OK + 1))
        else
            SIGN_FAIL=$((SIGN_FAIL + 1))
        fi
    done

else
    echo "  WARN: binary-sign-tool not found at ${BINARY_SIGN_TOOL}, skipping signing"
    SIGN_SKIP=$(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -ci 'ELF' || echo "0")
fi

echo "  OK: signed=$SIGN_OK failed=$SIGN_FAIL(.unsigned) skipped=$SIGN_SKIP"

# ================================================================
# Step 8: 统一修复执行权限 (必做!)
# ================================================================
# packaging.md Step 8 (CRITICAL):
#   根因: binary-sign-tool 签名后将权限重置为 660 (rw-rw----)
#   即使之前 chmod a+x 也被覆盖
#   必须在签名完成后、tar 打包前统一恢复
#   包含验证步骤: 所有 ELF 文件必须有执行权限
#
echo "[Step 8/10] 统一修复执行权限 (CRITICAL)..."
FIXED_COUNT=0

# 8a. 所有 ELF 文件添加执行权限
for _elf in $(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -iE 'ELF.*(shared|executable|relocatable)' | cut -d: -f1); do
    if [ -x "$_elf" ]; then
        : # 已有执行权限
    else
        chmod +x "$_elf" 2>/dev/null || true
        FIXED_COUNT=$((FIXED_COUNT + 1))
    fi
done

# 8b. bin/ 下的脚本也确保有执行权限
find "${PKGDIR}/bin" -type f ! -executable -exec chmod +x {} \; 2>/dev/null || true

echo "  OK: fixed permissions on $FIXED_COUNT files"

# 8c. 验证 (必做检查项)
echo "[Step 8c] 权限验证..."
NO_EXE_COUNT=0
_NO_EXE_LIST=""
for _elf in $(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -i ELF | cut -d: -f1); do
    if [ -x "$_elf" ]; then
        :
    else
        NO_EXE_COUNT=$((NO_EXE_COUNT + 1))
        _NO_EXE_LIST="${_NO_EXE_LIST}  missing exe: $(basename "$_elf")
"
    fi
done

if [ "$NO_EXE_COUNT" -gt 0 ]; then
    echo "  ERROR: $NO_EXE_COUNT ELF files still lack execute permission!"
    printf "%s\n" "$_NO_EXE_LIST"
    echo "  This will cause 'Permission denied' after tar extraction."
    echo "  Attempting force fix..."
    find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -i ELF | cut -d: -f1 | xargs chmod +x 2>/dev/null || true
else
    echo "  OK: all ELF files have execute permission"
fi

# 8d. 签名完整性检查
_UNSIGNED_COUNT=$(find "$PKGDIR" -name '*.unsigned' 2>/dev/null | wc -l | tr -d ' ')
if [ "$_UNSIGNED_COUNT" -gt 0 ]; then
    echo "  WARN: $_UNSIGNED_COUNT files unsigned (see *.unsigned markers)"
else
    echo "  OK: all ELF files signed (or signing skipped)"
fi

# ================================================================
# Step 9: 创建 install.sh (单独托管, 不打包进 tar.gz)
# ================================================================
# packaging.md Step 9 (v2.3):
#   - 基于 scripts/install-template.sh 生成
#   - 只修改 PKG_NAME 和 PKG_VERSION 两行
#   - install.sh 单独托管在 gitcode releases
#   - 禁止事项: heredoc / emoji / --strip-components / set -e / [[ ]] / source
#
echo "[Step 9/10] 生成 install.sh..."

_INSTALL_SH="${PACKAGING_DIR}/install-${SOFTWARE_NAME}-${VERSION}.sh"

# 基于模板生成 install.sh (纯 POSIX sh, 无 heredoc, 无 emoji)
printf '#!/bin/sh\n' > "$_INSTALL_SH"
printf '# %s for HarmonyOS — install.sh\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '# curl -fsSL <url>/install-%s.sh | sh -s -- <version>\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '#\n' >> "$_INSTALL_SH"
printf '# tar.gz is flat structure (bin/ share/ lib/ at top level)\n' >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf 'VER="${1:-%s}"\n' "$VERSION" >> "$_INSTALL_SH"
printf '[ -z "$VER" ] && { echo "Usage: sh install-%s.sh <version>"; exit 1; }\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf 'TMP="$HOME/tmp/install-%s-$$"\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf 'DST="$HOME/usr/local"\n' >> "$_INSTALL_SH"
printf 'URL="https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/%s/%s-${VER}-ohos-aarch64.tar.gz"\n' "$SOFTWARE_NAME" "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf 'mkdir -p "$TMP" "$DST" || exit 1\n' >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf '# 1. Download\n' >> "$_INSTALL_SH"
printf 'curl -fSL -o "$TMP/%s.tar.gz" "$URL" || { rm -rf "$TMP"; echo "Download failed"; exit 1; }\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf '# 2. Extract + Install (flat structure)\n' >> "$_INSTALL_SH"
printf 'tar xzf "$TMP/%s.tar.gz" -C "$TMP"\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf 'rm -f "$TMP/%s.tar.gz"\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf 'cp -r "$TMP"/* "$DST/"\n' >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf '# 3. Cleanup\n' >> "$_INSTALL_SH"
printf 'rm -rf "$TMP"\n' >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf '# 4. Permissions + PATH\n' >> "$_INSTALL_SH"
printf 'chmod +x "$DST/bin/"* 2>/dev/null || true\n' >> "$_INSTALL_SH"
# PATH append line (avoiding nested quote issues)
_PATH_LINE='grep -q "usr/local/bin" "$HOME/.zshrc" 2>/dev/null || echo '"'"'export PATH="$HOME/usr/local/bin:$PATH"'"'"' >> "$HOME/.zshrc"'
printf '%s\n' "$_PATH_LINE" >> "$_INSTALL_SH"
printf '\n' >> "$_INSTALL_SH"
printf '=== %s $VER installed ===\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"
printf '"$DST/bin/%s" --version | head -1\n' "$SOFTWARE_NAME" >> "$_INSTALL_SH"

chmod +x "$_INSTALL_SH"
echo "  OK: install.sh generated at ${_INSTALL_SH}"

# ================================================================
# Step 10: 打包 tar.gz (扁平结构)
# ================================================================
# packaging.md Step 10:
#   - 扁平结构: 解压顶层就是 bin/ share/ lib/ (禁止嵌套)
#   - 打包命令必须从包含 bin/ 的目录 (PKGDIR) 执行
#   - 10a. 主包 (干净产物: bin/ + lib/ + share/, 不含 install.sh)
#   - 10b. Debug 符号包 (--debug 时)
#   - 10c. 最终统计
#   - 10d. 安装验证 (模拟解压 + 执行)
#
echo "[Step 10/10] 打包 tar.gz..."

_ARCH="ohos-aarch64"
_TARBALL_NAME="${SOFTWARE_NAME}-${VERSION}-${_ARCH}.tar.gz"

# 10a. 主包 (从 PKGDIR 内部打包, 保证扁平结构)
cd "$PKGDIR"
tar czf "${PACKAGING_DIR}/${_TARBALL_NAME}" bin lib include share doc 2>/dev/null || \
tar czf "${PACKAGING_DIR}/${_TARBALL_NAME}" bin lib share 2>/dev/null || true
cd "$PROJECT_DIR"

_TARBALL_SIZE=$(du -h "${PACKAGING_DIR}/${_TARBALL_NAME}" 2>/dev/null | cut -f1)
echo "  OK: main package ${_TARBALL_NAME} (${_TARBALL_SIZE})"

# 10b. Debug 符号包
if [ "$DEBUG_BUILD" = true ] && [ -d "$DEBUG_DIR" ] && [ "$(ls -A "$DEBUG_DIR" 2>/dev/null)" ]; then
    _DEBUG_TARBALL="${SOFTWARE_NAME}-${VERSION}-${_ARCH}-debug.tar.gz"
    tar czf "${PACKAGING_DIR}/${_DEBUG_TARBALL}" -C "$DEBUG_DIR" . 2>/dev/null
    _DEBUG_SIZE=$(du -h "${PACKAGING_DIR}/${_DEBUG_TARBALL}" 2>/dev/null | cut -f1)
    echo "  OK: debug package ${_DEBUG_TARBALL} (${_DEBUG_SIZE})"
fi

# 10c. 最终统计
echo ""
echo "=== Packaging Statistics ==="
_TOTAL_FILES=$(find "$PKGDIR" -type f 2>/dev/null | wc -l | tr -d ' ')
_ELF_FILES=$(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -ci elf || echo "0")
_EXT_DEPS=$(find "${PKGDIR}/lib/external" -type f 2>/dev/null | wc -l | tr -d ' ')
_REMAINING_LINKS=$(find "$PKGDIR" -type l 2>/dev/null | wc -l | tr -d ' ')
echo "  Total files : $_TOTAL_FILES"
echo "  ELF files   : $_ELF_FILES"
echo "  Ext deps    : $_EXT_DEPS"
echo "  Symlinks    : $_REMAINING_LINKS (should be 0)"

# 10d. 安装验证 (模拟解压 + 版本检测)
_VERIFY_DIR="${TMPDIR:-$HOME/tmp}/pkg-verify-$$"
rm -rf "$_VERIFY_DIR" 2>/dev/null || true
mkdir -p "$_VERIFY_DIR"
if tar xzf "${PACKAGING_DIR}/${_TARBALL_NAME}" -C "$_VERIFY_DIR" 2>/dev/null; then
    chmod +x "$_VERIFY_DIR/bin/"* 2>/dev/null || true
    if [ -f "$_VERIFY_DIR/bin/$SOFTWARE_NAME" ]; then
        if "$_VERIFY_DIR/bin/$SOFTWARE_NAME" --version >/dev/null 2>&1; then
            echo "  Verify: PASS (./$SOFTWARE_NAME --version OK)"
        else
            echo "  Verify: WARN (./$SOFTWARE_NAME --version failed, may need args)"
        fi
    else
        echo "  Verify: INFO (no '$SOFTWARE_NAME' in bin/, manual check advised)"
    fi
else
    echo "  Verify: FAIL (tar extract failed)"
fi
rm -rf "$_VERIFY_DIR" 2>/dev/null || true

# ================================================================
# 完成
# ================================================================
echo ""
echo "============================================"
echo "  Packaging Complete!"
echo "============================================"
echo "  Artifacts:"
echo "    main: ${PACKAGING_DIR}/${_TARBALL_NAME}"
[ "$DEBUG_BUILD" = true ] && [ -f "${PACKAGING_DIR}/${SOFTWARE_NAME}-${VERSION}-${_ARCH}-debug.tar.gz" ] && \
    echo "  debug: ${PACKAGING_DIR}/${SOFTWARE_NAME}-${VERSION}-${_ARCH}-debug.tar.gz"
echo "  install: ${_INSTALL_SH}"
[ "$DEBUG_BUILD" = true ] && echo "  symbols: ${DEBUG_DIR}/"
echo "  archive: ${ARCHIVE_DIR}"
echo "============================================"
