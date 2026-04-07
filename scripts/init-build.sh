#!/bin/sh
# init-build.sh — 编译初始化（Phase 0 → 2 一条命令）
# 用法:
#   ./scripts/init-build.sh <软件名> [--auto]           # 全自动（默认）
#   ./scripts/init-build.sh <软件名> [<版本>] [--ask]    # 交互式（缺省信息时询问）
#   ./scripts/init-build.sh --resume                     # 恢复上次上下文
#   ./scripts/init-build.sh <软件名> [<版本>] [--url=URL] [--tar=tar.gz]
#
# 输出: .build-context-<name>-<version> 文件（AI 读取后即可开始 Phase 3）
#
# 模式说明:
#   --auto:   注册表有记录时全自动执行，失败则退出
#   --ask:    缺少 URL/版本等信息时输出提示供 AI/用户补充
#   --resume: 从已有的 .build-context 恢复（会话中断后用）
#
# Layer: Layer2（应该工具化但保留 AI 兜底）

set -e

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REGISTRY_FILE="${PROJECT_DIR}/scripts/software-registry.yaml"
TMPDIR="${TMPDIR:-$HOME/tmp}"
BUILD_DIR="${TMPDIR}/builds"

# ---------- 帮助 ----------
show_help() {
    cat <<'HELPEOF'
用法:
  ./scripts/init-build.sh <软件名> [选项]

描述:
  编译初始化管线。自动完成 Phase 0(下载)→Phase 1(检索)→Phase 1.5(骨架)→Phase 2(环境检查)。
  输出 .build-context 文件，AI 读取后可直接开始 Phase 3 编译。

模式:
  --auto     全自动（默认）。使用注册表信息，失败时退出。
  --ask      交互式。缺少信息时输出提示，等待 AI 补充参数。
  --resume   恢复。从已有 .build-context 重建环境变量。

选项:
  --version=VER   指定版本号（不指定则用注册表最新版）
  --url=URL       自定义下载 URL（覆盖注册表）
  --tar=FMT       强制指定格式：tar.gz / tar.xz / tar.bz2 / zip
  --no-download   跳过下载（源码已存在时）

示例:
  ./scripts/init-build.sh sed                      # 自动下载 sed 最新版
  ./scripts/init-build.sh sed 4.9                  # 指定版本
  ./scripts/init-build.sh sed --url=https://...    # 自定义 URL
  ./scripts/init-build.sh --resume                 # 恢复上次

输出文件:
  .build-context-<name>-<version>  — JSON 格式上下文文件

依赖:
  - scripts/software-registry.yaml  — 软件元数据注册表
  - scripts/init-archive.sh        — 档案骨架创建
  - scripts/check-env.sh           — 环境检查
HELPEOF
    exit 0
}

# ---------- YAML 简易解析（POSIX sh 兼容）----------
# 从 registry 中读取单个字段的值
# 用法: registry_get <software_name> <field>
registry_get() {
    _name="$1"
    _field="$2"
    # 在 registry 的 "  _name:" 块中查找 "_field:" 行并取值
    # 处理多行值（如 known_issues 列表）和单行值
    _in_block=0
    _result=""
    while IFS= read -r _line; do
        case "$_line" in
            "  ${_name}:")
                _in_block=1
                continue
                ;;
            "  "*":")
                [ "$_in_block" = "1" ] && _in_block=0 && break
                continue
                ;;
        esac
        if [ "$_in_block" = "1" ]; then
            case "$_line" in
                "    ${_field}:"*)
                    _val=$(echo "$_line" | sed "s/    ${_field}: *//")
                    # 去除 YAML 引号
                    _val=$(echo "$_val" | sed 's/^"//;s/"$//')
                    if [ -z "$_result" ]; then
                        _result="$_val"
                    else
                        _result="${_result}
${_val}"
                    fi
                    ;;
            esac
        fi
    done < "$REGISTRY_FILE"
    printf '%s' "$_result"
}

# ---------- 自动发现（registry 未命中时）----------
# 搜索候选 URL，输出供选择，返回选中的 URL 或空
auto_discover() {
    _name="$1"
    _ver="$2"
    
    echo ""
    echo "  🔍 注册表未命中，启动自动搜索..."
    echo ""
    
    # 调用搜索辅助工具
    if [ -x "${SCRIPT_DIR}/search-download-url.sh" ]; then
        "${SCRIPT_DIR}/search-download-url.sh" "$_name" "$_ver" 2>&1 \
            | while IFS= read -r line; do printf '     %s\n' "$line"; done
    else
        # 内联简化版搜索（当 search-download-url.sh 不可用时）
        log_warn "search-download-url.sh 不可用，使用内置搜索..."
        for base in \
            "https://ftp.gnu.org/gnu/${_name}" \
            "https://github.com/${_name}/${_name}/releases/download/v${_ver}"; do
            log_info "尝试: ${base}/${_name}-${_ver}.tar.*"
        done
    fi
    
    echo ""
    echo "  💡 请从上方 ✅ 标记的 URL 中选择一个，然后："
    echo "     ./scripts/init-build.sh ${_name} ${_ver} --url=<选中URL>"
    echo ""
}

# ---------- 运行时追加到 registry ----------
# 用法: registry_append <name> <url_template> [build_system] [tar_format]
registry_append() {
    _aname="$1"
    _aurl="$2"
    _abuild="${3:-unknown}"
    _afmt="${4:-tar.gz}"
    
    # 检查是否已存在
    if grep -q "^  ${_aname}:" "$REGISTRY_FILE" 2>/dev/null; then
        log_warn "registry 中已有 ${_aname}，跳过追加"
        return 0
    fi
    
    # 在 registry: 前一行插入新条目
    _tmp="${REGISTRY_FILE}.tmp.$$"
    _first_letter="$(echo "$_aname" | cut -c1 | tr 'A-Z' 'a-z')"
    
    awk -v name="$_aname" -v url="$_aurl" -v build="$_abuild" -v fmt="$_afmt" '
        /^registry:/ && !inserted {
            print "  "name":"
            print "    display: \""name"\""
            print "    category: auto-discovered"
            print "    build_system: "build
            print "    url_template: \""url"\""
            print "    url_fallback: \"\""
            print "    checksum_url: \"\""
            print "    tar_format: \""fmt"\""
            print "    static_build: false"
            print "    known_issues: []"
            print "    status: pending"
            print ""
            inserted = 1
        }
        { print }
    ' "$REGISTRY_FILE" > "$_tmp"
    
    if [ -s "$_tmp" ]; then
        mv "$_tmp" "$REGISTRY_FILE"
        log_info "已自动注册到 software-registry.yaml: ${_aname}"
    else
        rm -f "$_tmp"
        log_warn "registry 追加失败（文件写入异常），不影响编译流程"
    fi
}

# ---------- 日志 ----------
log_info() { printf '  ✅ %s\n' "$*"; }
log_warn() { printf '  ⚠️  %s\n' "$*"; }
log_error() { printf '  ❌ %s\n' "$*" >&2; }
log_ask() { printf '  ❓ %s\n' "$*"; }

# ---------- 参数解析 ----------
MODE="auto"
SOFTWARE_NAME=""
VERSION=""
CUSTOM_URL=""
CUSTOM_TAR_FMT=""
NO_DOWNLOAD=false

if [ $# -lt 1 ]; then
    log_error "缺少参数"
    show_help
    exit 1
fi

case "$1" in
    --help|-h) show_help ;;
    --resume)
        MODE="resume"
        ;;
    -*)
        log_error "未知选项: $1"
        exit 1
        ;;
    *)
        SOFTWARE_NAME="$1"
        shift
        ;;
esac

while [ $# -gt 0 ]; do
    case "$1" in
        --auto)   MODE="auto"; shift ;;
        --ask)    MODE="ask"; shift ;;
        --resume) MODE="resume"; shift ;;
        --version=*) VERSION="${1#--version=}"; shift ;;
        --url=*)      CUSTOM_URL="${1#--url=}"; shift ;;
        --tar=*)      CUSTOM_TAR_FMT="${1#--tar=}"; shift ;;
        --no-download) NO_DOWNLOAD=true; shift ;;
        [0-9]*|v[0-9]*)  # 位置参数版本号 (如 0.29.2 或 v0.29.2)
            VERSION=$(echo "$1" | sed 's/^v//')
            shift ;;
        *) shift ;;  # 忽略未知参数
    esac
done

# ══════════════════════════════════════════
#  --resume 模式
# ══════════════════════════════════════════
if [ "$MODE" = "resume" ]; then
    echo "🔄 恢复编译上下文..."
    
    # 查找最新的 .build-context 文件
    CONTEXT_FILE=$(ls -t "${PROJECT_DIR}/.build-context"-* 2>/dev/null | head -1)
    
    if [ -z "$CONTEXT_FILE" ] || [ ! -f "$CONTEXT_FILE" ]; then
        log_error "找不到 .build-context 文件"
        log_error "请先运行: ./scripts/init-build.sh <软件名>"
        exit 2
    fi
    
    log_info "找到上下文: $(basename "$CONTEXT_FILE")"
    
    # 输出环境变量设置命令
    echo ""
    echo "=== 请执行以下命令恢复编译环境 ==="
    echo ""
    cat "$CONTEXT_FILE"
    echo ""
    echo "=========================================="
    exit 0
fi

# ══════════════════════════════════════════
#  主流程: Phase 0 → 2
# ══════════════════════════════════════════

echo "🏗️  编译初始化管线"
echo "  软件:   ${SOFTWARE_NAME}${VERSION:+ v${VERSION}}"
echo "  模式:   ${MODE}"
echo ""

# ---- Step 1: 查询注册表 ----
echo "[1/8] 查询软件元数据..."

IN_REGISTRY=false
if grep -q "^  ${SOFTWARE_NAME}:" "$REGISTRY_FILE" 2>/dev/null; then
    IN_REGISTRY=true
    
    REG_URL_TEMPLATE=$(registry_get "$SOFTWARE_NAME" "url_template")
    REG_FALLBACK=$(registry_get "$SOFTWARE_NAME" "url_fallback")
    REG_BUILD_SYS=$(registry_get "$SOFTWARE_NAME" "build_system")
    REG_TAR_FMT=$(registry_get "$SOFTWARE_NAME" "tar_format")
    REG_LATEST_VER=$(registry_get "$SOFTWARE_NAME" "latest_version")
    REG_STATIC=$(registry_get "$SOFTWARE_NAME" "static_build")
    REG_ISSUES=$(registry_get "$SOFTWARE_NAME" "known_issues")
    
    log_info "注册表命中: build_system=${REG_BUILD_SYS}, format=${REG_TAR_FMT}"
else
    log_warn "注册表中无此软件（首次遇到）"
    # 不退出！继续尝试 --url 参数或自动降级
fi

# 版本号确定
if [ -z "$VERSION" ]; then
    if [ -n "$REG_LATEST_VER" ]; then
        VERSION="$REG_LATEST_VER"
        log_info "使用注册表版本: $VERSION"
    else
        # 版本未指定且 registry 无记录 → 需要更多信息
        if [ -z "$CUSTOM_URL" ]; then
            log_warn "需要版本号或下载 URL（注册表无此软件）"
            log_ask "请提供后重试:"
            log_ask "  ./scripts/init-build.sh ${SOFTWARE_NAME} <VERSION> [--url=URL]"
            # 如果连名字都是新的，直接触发搜索
            if [ "$IN_REGISTRY" = "false" ]; then
                auto_discover "$SOFTWARE_NAME" "${VERSION:-latest}"
            fi
            exit 1
        fi
        # 有 --url 但无版本 → 从 URL 推断或继续
        log_info "使用自定义 URL，跳过版本验证"
    fi
fi

# 构建系统确定
BUILD_SYSTEM="${REG_BUILD_SYSTEM:-unknown}"

# tar 格式确定
TAR_FORMAT="${CUSTOM_TAR_FMT:-$REG_TAR_FMT}"
if [ -z "$TAR_FORMAT" ]; then
    TAR_FORMAT="tar.gz"  # 默认值
fi

# ---- Step 2: 确定 URL ----
echo "[2/8] 确定下载 URL..."

DOWNLOAD_URL=""
if [ -n "$CUSTOM_URL" ]; then
    DOWNLOAD_URL="$CUSTOM_URL"
    log_info "使用自定义 URL"
elif [ -n "$REG_URL_TEMPLATE" ]; then
    DOWNLOAD_URL=$(echo "$REG_URL_TEMPLATE" | sed "s/{version}/${VERSION}/g")
    log_info "URL: $(echo "$DOWNLOAD_URL" | sed "s|${VERSION}|{version}|g")"
elif [ -n "$REG_FALLBACK" ]; then
    DOWNLOAD_URL=$(echo "$REG_FALLBACK" | sed "s/{version}/${VERSION}/g")
    log_info "使用备用 URL"
else
    # registry 未命中且无 URL → 自动降级搜索
    if [ "$IN_REGISTRY" = "false" ]; then
        auto_discover "$SOFTWARE_NAME" "${VERSION:-latest}"
        exit 1
    else
        log_error "注册表条目存在但缺少 URL（数据不完整）"
        exit 3
    fi
fi

# ---- Step 2.5: 首次遇到新软件 → 自动注册到 registry ----
if [ "$IN_REGISTRY" = "false" ] && [ -n "$DOWNLOAD_URL" ]; then
    # 推断构建系统（从 URL 或回退到 unknown）
    GUESS_BUILD_SYS="${REG_BUILD_SYS:-unknown}"
    if [ "$GUESS_BUILD_SYS" = "unknown" ] || [ -z "$GUESS_BUILD_SYS" ]; then
        case "$DOWNLOAD_URL" in
            *gnu.org*|*savannah*|*nongnu*)   GUESS_BUILD_SYS="autotools" ;;
            *cmake*|*kitware*)                 GUESS_BUILD_SYS="cmake" ;;
            *github.com*/mesonbuild/*)         GUESS_BUILD_SYS="meson" ;;
            *openssl*)                         GUESS_BUILD_SYS="custom-perl" ;;
            *)                                 GUESS_BUILD_SYS="unknown" ;;
        esac
    fi
    
    # 推断 tar 格式
    GUESS_TAR_FMT="${TAR_FORMAT:-tar.gz}"
    case "$DOWNLOAD_URL" in
        *.tar.xz|*.txz)  GUESS_TAR_FMT="tar.xz" ;;
        *.tar.bz2|*.tbz2) GUESS_TAR_FMT="tar.bz2" ;;
        *.zip)           GUESS_TAR_FMT="zip" ;;
    esac
    
    BUILD_SYSTEM="$GUESS_BUILD_SYS"
    TAR_FORMAT="$GUESS_TAR_FMT"
    
    registry_append "$SOFTWARE_NAME" "$DOWNLOAD_URL" "$BUILD_SYSTEM" "$TAR_FMT"
fi

# ---- Step 3: 下载源码 ----
TARBALL_NAME="${SOFTWARE_NAME}-${VERSION}.${TAR_FORMAT}"
TARBALL_PATH="${BUILD_DIR}/${TARBALL_NAME}"
SRC_DIR="${BUILD_DIR}/${SOFTWARE_NAME}-${VERSION}"

if [ "$NO_DOWNLOAD" = "true" ]; then
    echo "[3/8] ⏭️  跳过下载（--no-download）"
    if [ ! -d "$SRC_DIR" ]; then
        log_error "--no-download 但源码目录不存在: $SRC_DIR"
        exit 2
    fi
    log_info "源码目录已存在: $SRC_DIR"
else
    echo "[3/8] 下载源码..."
    mkdir -p "$BUILD_DIR"
    
    if [ -f "$TARBALL_PATH" ]; then
        log_info "Tarball 已存在: $(du -h "$TARBALL_PATH" | cut -f1)"
    else
        log_info "下载: $DOWNLOAD_URL"
        
        # 尝试下载（带重试和超时）
        DL_RESULT=0
        curl -fSL --connect-timeout 15 --max-time 300 \
             -o "$TARBALL_PATH" "$DOWNLOAD_URL" 2>/dev/null || DL_RESULT=$?
        
        if [ "$DL_RESULT" -ne 0 ]; then
            rm -f "$TARBALL_PATH"
            
            # 尝试备用 URL
            if [ -n "$REG_FALLBACK" ] && [ -z "$CUSTOM_URL" ]; then
                FALLBACK_URL=$(echo "$REG_FALLBACK" | sed "s/{version}/${VERSION}/g")
                log_warn "主 URL 失败，尝试备用..."
                curl -fSL --connect-timeout 15 --max-time 300 \
                     -o "$TARBALL_PATH" "$FALLBACK_URL" 2>/dev/null || DL_RESULT=$?
            fi
            
            if [ "$DL_RESULT" -ne 0 ]; then
                rm -f "$TARBALL_PATH"
                log_error "下载失败 (curl exit code: $DL_RESULT)"
                
                if [ "$MODE" = "ask" ]; then
                    log_ask "请手动下载后放到: $TARBALL_PATH"
                    log_ask "或使用: --no-download 跳过（如果已解压）"
                fi
                exit 3
            fi
        fi
        
        # 验证不是 HTML 错误页
        if head -1 "$TARBALL_PATH" 2>/dev/null | grep -q '<!DOCTYPE\|<html'; then
            rm -f "$TARBALL_PATH"
            log_error "下载内容是 HTML 页面（非 tarball），URL 可能错误"
            exit 3
        fi
        
        SIZE=$(du -h "$TARBALL_PATH" | cut -f1)
        log_info "下载完成: $TARBALL_NAME ($SIZE)"
    fi
fi

# ---- Step 4: 解压源码 ----
echo "[4/8] 解压源码..."

if [ -d "$SRC_DIR" ] && [ -f "$SRC_DIR/configure" -o -f "$SRC_DIR/CMakeLists.txt" -o -f "$SRC_DIR/Makefile" -o -f "$SRC_DIR/Configure" ]; then
    log_info "源码目录已存在: $SRC_DIR"
else
    # 清理可能的不完整解压
    rm -rf "$SRC_DIR"
    
    case "$TAR_FORMAT" in
        tar.gz|tgz)  TAR_FLAG="xzf" ;;
        tar.xz|txz)  TAR_FLAG="xJf" ;;
        tar.bz2|tbz2) TAR_FLAG="xjf" ;;
        zip)         UNZIP=true ;;
        *)           TAR_FLAG="xzf" ;;  # 默认
    esac
    
    if [ "$UNZIP" = "true" ]; then
        cd "$BUILD_DIR" && unzip -q "$TARBALL_PATH" 2>/dev/null
    else
        tar $TAR_FLAG "$TARBALL_PATH" -C "$BUILD_DIR" 2>/dev/null
    fi
    
    # 检查解压结果
    if [ ! -d "$SRC_DIR" ]; then
        # 可能解压为子目录
        EXTRACTED=$(find "$BUILD_DIR" -maxdepth 1 -type d -name "${SOFTWARE_NAME}-*" | head -1)
        if [ -n "$EXTRACTED" ] && [ "$EXTRACTED" != "$SRC_DIR" ]; then
            mv "$EXTRACTED" "$SRC_DIR" 2>/dev/null || true
        fi
    fi
    
    if [ -d "$SRC_DIR" ]; then
        log_info "解压完成: $SRC_DIR"
    else
        log_error "解压失败，无法找到源码目录"; exit 3
    fi
fi

# ---- Step 5: 检索历史档案 ----
echo "[5/8] 检索历史档案..."

FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"
ARCHIVE_DIR="${PROJECT_DIR}/archives/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}"
HISTORY_FOUND=false
HISTORY_STATUS=""

if [ -d "$ARCHIVE_DIR" ]; then
    HISTORY_FOUND=true
    HISTORY_MANIFEST="${ARCHIVE_DIR}/manifest.yaml"
    if [ -f "$HISTORY_MANIFEST" ]; then
        HISTORY_STATUS=$(grep '^status:' "$HISTORY_MANIFEST" 2>/dev/null | head -1 | sed 's/status: *//')
        log_info "历史档案: $HISTORY_STATUS"
        
        # 统计已有补丁
        PATCH_COUNT=$(find "$ARCHIVE_DIR/patches" -name "000*.patch" -type f 2>/dev/null | wc -l | tr -d ' ')
        if [ "$PATCH_COUNT" -gt 0 ]; then
            log_info "已有补丁: $PATCH_COUNT 个"
        fi
    else
        log_info "历史档案目录存在但无 manifest（不完整归档）"
    fi
else
    log_info "无历史档案（首次编译）"
fi

# ---- Step 6: 创建/恢复档案骨架 ----
echo "[6/8] 创建档案骨架..."

if [ "$HISTORY_FOUND" = "true" ] && [ "$HISTORY_STATUS" = "compiling" ]; then
    log_info "档案已存在且状态为 compiling，跳过创建"
elif [ -x "${SCRIPT_DIR}/init-archive.sh" ]; then
    # 调用已有脚本
    "${SCRIPT_DIR}/init-archive.sh" "$SOFTWARE_NAME" "$VERSION" "$DOWNLOAD_URL" "$BUILD_SYSTEM" 2>&1 \
        | while IFS= read -r line; do printf '     %s\n' "$line"; done
else
    # 手动创建最小骨架
    mkdir -p "$ARCHIVE_DIR"/{patches,reports,scripts,logs}
    log_info "手动创建骨架: $ARCHIVE_DIR"
fi

# ---- Step 7: 环境检查 ----
echo "[7/8] 环境检查..."

if [ -x "${SCRIPT_DIR}/check-env.sh" ]; then
    "${SCRIPT_DIR}/check-env.sh" 2>&1 | while IFS= read -r line; do printf '     %s\n' "$line"; done
else
    # 最小化环境检查
    for var in CC CFLAGS DEFAULT_PREFIX TMPDIR; do
        eval "val=\$$var"
        if [ -z "$val" ]; then
            log_warn "\$${var} 未设置"
        fi
    done
fi

# ---- Step 8: 输出上下文文件 ----
echo "[8/8] 生成编译上下文..."

CONTEXT_FILE="${PROJECT_DIR}/.build-context-${SOFTWARE_NAME}-${VERSION}"

cat > "$CONTEXT_FILE" <<CTXEOF
# ============================================================
# BUILD CONTEXT — ${SOFTWARE_NAME} ${VERSION}
# 由 init-build.sh 自动生成
# AI 读取此文件后即可开始 Phase 3 编译执行
# ============================================================

# --- 基本信息 ---
export BUILD_SOFTWARE="${SOFTWARE_NAME}"
export BUILD_VERSION="${VERSION}"
export BUILD_SYSTEM="${BUILD_SYSTEM}"
export BUILD_MODE="${MODE}"

# --- 路径 ---
export BUILD_TARBALL="${TARBALL_PATH}"
export BUILD_SRC_DIR="${SRC_DIR}"
export BUILD_ARCHIVE_DIR="${ARCHIVE_DIR}"
export BUILD_CONTEXT_FILE="${CONTEXT_FILE}"

# --- 下载信息 ---
export BUILD_URL="${DOWNLOAD_URL}"
export BUILD_TAR_FORMAT="${TAR_FORMAT}"

# --- 历史档案 ---
export BUILD_HISTORY_FOUND="${HISTORY_FOUND}"
export BUILD_HISTORY_STATUS="${HISTORY_STATUS}"

# --- 已知问题 ---
# 以下来自注册表，AI 应在 Phase 3 编译时关注：
CTXEOF

# 追加已知问题（如果有）
if [ -n "$REG_ISSUES" ]; then
    echo "# 已知鸿蒙适配问题:" >> "$CONTEXT_FILE"
    echo "$REG_ISSUES" | while IFS= read -r issue; do
        [ -n "$issue" ] && echo "#   - ${issue}" >> "$CONTEXT_FILE"
    done
fi

# 追加静态库要求
if [ "$REG_STATIC" = "true" ]; then
    echo "" >> "$CONTEXT_FILE"
    echo "# ⚠️ 静态编译要求: 此软件在 dependencies.md 危险库分级表中标记为必须静态" >> "$CONTEXT_FILE"
fi

cat >> "$CONTEXT_FILE" <<'CTXEOF'

# --- 下一步 ---
# AI 请执行以下操作:
#   1. 读取 PROGRESS.md:  cat ${BUILD_ARCHIVE_DIR}/PROGRESS.md
#   2. 进入源码目录:  cd ${BUILD_SRC_DIR}
#   3. 执行 Phase 3 编译:
#      a. 如有历史补丁:  for p in ${BUILD_ARCHIVE_DIR}/patches/*.patch; do patch -p1 < $p; done
#      b. ./configure --prefix=${DEFAULT_PREFIX}  (或其他必要参数)
#      c. make -j1
#      d. make install
#      e. 触发安全弹窗:  ${BUILD_SRC_DIR}/.../<binary> --version
#   4. 编译成功后执行:
#      ./scripts/finish-build.sh ${BUILD_SOFTWARE} ${BUILD_VERSION} success
# ============================================================
CTXEOF

log_info "上下文文件: $CONTEXT_FILE"

# ---- 完成 ----
echo ""
echo "════════════════════════════════════════"
echo "✅ 编译初始化完成"
echo ""
echo "  📦 软件:   ${SOFTWARE_NAME} ${VERSION}"
echo "  🔧 构建:   ${BUILD_SYSTEM}"
echo "  📂 源码:   ${SRC_DIR}"
echo "  📋 归档:   ${ARCHIVE_DIR}"
echo "  📄 上下文: ${CONTEXT_FILE}"
echo ""

if [ -n "$REG_ISSUES" ]; then echo "  ⚠️  已知问题:"; echo "$REG_ISSUES" | while IFS= read -r i; do [ -n "$i" ] && echo "     - $i"; done; fi

echo ""
echo "  下一步: 开始 Phase 3 编译执行"
echo "         或: ./scripts/init-build.sh --resume  (查看上下文)"
echo "════════════════════════════════════════"
