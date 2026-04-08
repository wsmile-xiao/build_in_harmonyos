#!/bin/sh
# ==============================================================================
# [Layer 1] init-archive.sh - 编译档案骨架创建/恢复（全自动）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性目录创建和模板填充）
# 入口: ./scripts/init-archive.sh <软件名> <版本> [源码URL] [构建系统] [--clean]
# 依赖: templates/PROGRESS.md（可选，有则用模板）
# 调用者: init-build.sh, AI / 用户
# ==============================================================================
# init-archive.sh - 创建/恢复编译档案骨架（Phase 1.5）
# 用法: ./init-archive.sh <软件名> <版本> [源码下载URL] [构建系统类型]
#
# 核心原则: 重编译时最大化复用已有归档内容，不主动删除任何文件。
#   - manifest.yaml / PROGRESS.md / README.md → 有实质内容则保留
#   - patches/*.patch → 全部保留（AI 在 Step 2 可选择性应用）
#   - reports/* / packaging/* / logs/* → 全部保留（历史记录）
#   - *.tmp / .bak 等临时文件 → 不在此处清理，由最终归档收口步骤处理
#   - 只有 --clean 标志才强制清空 patches/ 和 packaging/（用于完全重置场景）
#
# 关键改进：检测到已有非空档案时保留 PROGRESS.md 和 manifest.yaml，
# 不再用空模板覆盖历史记录。

set -e

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVES_DIR="${PROJECT_DIR}/archives"

show_help() {
    cat <<'HELPEOF'
用法:
  ./init-archive.sh <软件名> <版本> [源码下载URL] [构建系统类型]

描述:
  创建或恢复编译档案骨架（Phase 1.5），包括：
  - 目录结构：archives/{letter}/{name}/{version}/{patches,reports,packaging}
  - manifest.yaml（编译元数据，已有则保留）
  - PROGRESS.md（编译进度跟踪，已有则保留）
  - README.md（编译说明，已有则保留）
  - _meta.yaml 索引元数据

重编译行为:
  - 默认模式: 保留所有已有文件（复用旧补丁/报告/PROGRESS），仅创建缺失的骨架
  - --clean: 清空 patches/ 和 packaging/（完全重置，用于丢弃旧补丁重新开始）

参数:
  <软件名>          软件名称（如 openssl, zlib, curl）
  <版本>            版本号（如 3.0.1, 1.2.13）
  [源码下载URL]     源码下载地址（可选）
  [构建系统类型]    构建系统类型：cmake|autotools|meson|make|custom（默认 unknown）
  [--clean]         强制清空 patches/ 和 packaging/（完全重置模式）

退出码:
  0  成功
  1  参数错误
  2  目录创建失败
HELPEOF
    exit 0
}

# ---------- 参数检查 ----------
if [ $# -lt 2 ]; then
    echo "❌ 缺少必要参数。使用 --help 查看帮助。"
    exit 1
fi

case "$1" in
    --help|-h)
        show_help
        ;;
esac

SOFTWARE_NAME="$1"
VERSION="$2"
SOURCE_URL="${3:-}"
BUILD_SYSTEM="${4:-unknown}"
CLEAN_MODE="false"

# ---------- 路径遍历防护 ----------
sanitize_path_component() {
    echo "$1" | sed 's/[^a-zA-Z0-9._+-]//g'
}
SOFTWARE_NAME=$(sanitize_path_component "$SOFTWARE_NAME")
VERSION=$(sanitize_path_component "$VERSION")

# 解析可选参数
shift 4
for arg in "$@"; do
    case "$arg" in
        --clean) CLEAN_MODE="true" ;;
    esac
done

# ---------- 计算首字母 ----------
FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"

# ---------- 构建路径 ----------
SOFTWARE_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}"
VERSION_DIR="${SOFTWARE_DIR}/${VERSION}"

echo "📝 创建/恢复编译档案骨架"
echo "  软件:   ${SOFTWARE_NAME}"
echo "  版本:   ${VERSION}"
echo "  构建:   ${BUILD_SYSTEM}"
if [ -n "$SOURCE_URL" ]; then
    echo "  源码:   ${SOURCE_URL}"
fi
echo "  路径:   ${VERSION_DIR}"
echo ""

# ---------- 步骤 1: 创建目录结构 ----------
echo "[1/6] 创建目录结构..."

# 注：不预创建 scripts/ 和 logs/ 目录（D3 优化）
# 原因：当前流程中没有任何步骤向这两个目录写入文件
# 如未来需要，可在对应步骤按需创建
SUBDIRS="patches reports packaging"
for subdir in $SUBDIRS; do
    _target="${VERSION_DIR}/${subdir}"
    if mkdir -p "$_target"; then
        echo "  ✅ ${subdir}/"
    else
        echo "  ❌ 创建目录失败: ${subdir}/"
        exit 2
    fi
done

# --clean 模式：清空 patches/ 和 packaging/（完全重置）
if [ "$CLEAN_MODE" = "true" ]; then
    echo "  🧹 [--clean] 清空旧补丁和打包产物..."
    rm -f "${VERSION_DIR}"/patches/*.patch 2>/dev/null || true
    rm -f "${VERSION_DIR}"/packaging/*.tar.gz "${VERSION_DIR}"/packaging/*.sh 2>/dev/null || true
    rm -rf "${VERSION_DIR}"/packaging/bin "${VERSION_DIR}"/packaging/debug "${VERSION_DIR}"/packaging/share 2>/dev/null || true
    echo "  ✅ patches/ 和 packaging/ 已清空"
fi

# ---------- 步骤 2: manifest.yaml（已有实质内容则保留）----------
TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
echo "[2/5] 检查 manifest.yaml..."

if [ -f "${VERSION_DIR}/manifest.yaml" ] && [ "$(wc -l < "${VERSION_DIR}/manifest.yaml" | tr -d ' ')" -gt 10 ]; then
    echo "  ✅ manifest.yaml 已存在（$(wc -l < "${VERSION_DIR}/manifest.yaml" | tr -d ' ') 行），保留"
else
    cat > "${VERSION_DIR}/manifest.yaml" <<EOF
# 编译档案 manifest
# 由 init-archive.sh 自动生成 / 恢复
# 生成时间: ${TIMESTAMP}

software: ${SOFTWARE_NAME}
version: ${VERSION}
status: compiling

build_system: ${BUILD_SYSTEM}
EOF
    if [ -n "$SOURCE_URL" ]; then
        printf 'source_url: %s\n' "$SOURCE_URL" >> "${VERSION_DIR}/manifest.yaml"
    fi
    printf '\n# 编译环境信息\ncreated_at: %s\n\n# 知识积累\nknowledge_gained: []\n\n# 补丁列表\npatches_applied: []\n\n# 编译日志\nbuild_log: logs/build.log\n' \
        "$TIMESTAMP" >> "${VERSION_DIR}/manifest.yaml"
    echo "  ✅ manifest.yaml 已创建"
fi

# ---------- 步骤 3: PROGRESS.md（已有实质内容则保留）----------
echo "[3/5] 检查 PROGRESS.md..."

if [ -f "${VERSION_DIR}/PROGRESS.md" ] && [ "$(wc -l < "${VERSION_DIR}/PROGRESS.md" | tr -d ' ')" -gt 15 ]; then
    echo "  ✅ PROGRESS.md 已存在（$(wc -l < "${VERSION_DIR}/PROGRESS.md" | tr -d ' ') 行），保留"
else
    # 使用 D4 规定的权威模板（templates/PROGRESS.md）
    _TEMPLATE_FILE="${PROJECT_DIR}/templates/PROGRESS.md"
    if [ -f "$_TEMPLATE_FILE" ]; then
        cp "$_TEMPLATE_FILE" "${VERSION_DIR}/PROGRESS.md"
        # 替换占位符
        sed -i "s/{{SOFTWARE_NAME}}/${SOFTWARE_NAME}/g" "${VERSION_DIR}/PROGRESS.md"
        sed -i "s/{{VERSION}}/${VERSION}/g" "${VERSION_DIR}/PROGRESS.md"
        sed -i "s/{{DATE}}/$(date '+%Y-%m-%d')/g" "${VERSION_DIR}/PROGRESS.md"
        sed -i "s/{{STATUS}}/initialized/g" "${VERSION_DIR}/PROGRESS.md"
        echo "  ✅ PROGRESS.md 已创建（来自权威模板 templates/PROGRESS.md）"
    else
        log_warn "templates/PROGRESS.md 不存在，使用内嵌模板"
        # Fallback：内嵌简化模板（原硬编码逻辑）
        cat > "${VERSION_DIR}/PROGRESS.md" <<EOF
# ${SOFTWARE_NAME} ${VERSION} — 编译进度

> 档案创建/恢复时间: ${TIMESTAMP}

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | ${SOFTWARE_NAME} |
| 版本 | ${VERSION} |
| 状态 | 🔵 编译中 |
| 构建系统 | ${BUILD_SYSTEM} |
EOF
        if [ -n "$SOURCE_URL" ]; then
            printf '| 源码路径 | %s |\n' "$SOURCE_URL" >> "${VERSION_DIR}/PROGRESS.md"
        fi
        cat >> "${VERSION_DIR}/PROGRESS.md" <<'PROGEOF'

## 编译阶段

### Phase 1: 环境准备
- [ ] 环境检查完成
- [ ] 源码下载完成

### Phase 2: 编译过程
- [ ] 配置完成
- [ ] 编译完成
- [ ] 安装完成

### Phase 3: 测试验证
- [ ] 功能测试
- [ ] 链接验证

### Phase 4: 归档收尾
- [ ] 知识提取
- [ ] 档案归档

## 发现与知识

<!-- 编译过程中发现的问题、解决方案和知识积累记录在这里 -->

PROGEOF
        echo "  ⚠️ PROGRESS.md 已创建（内嵌 fallback 模板，缺少 Phase 2.5 和对话记录）"
    fi
fi

# ---------- 步骤 4: README.md（已有实质内容则保留）----------
echo "[4/6] 检查 README.md..."

if [ -f "${VERSION_DIR}/README.md" ] && [ "$(wc -l < "${VERSION_DIR}/README.md" | tr -d ' ')" -gt 10 ]; then
    echo "  ✅ README.md 已存在（$(wc -l < "${VERSION_DIR}/README.md" | tr -d ' ') 行），保留"
else
    cat > "${VERSION_DIR}/README.md" <<EOF
# ${SOFTWARE_NAME} ${VERSION} for HarmonyOS/OpenHarmony

> **编译日期**: ${TIMESTAMP}
> **状态**: 🔵 编译中
> **构建系统**: ${BUILD_SYSTEM}

## 一、软件简介

（待编译完成后填写）

## 二、编译指导

（待编译完成后填写）

## 三、补丁清单

（待补丁生成后填写）

## 四、已知限制

（待测试后填写）

## 五、功能验证

（待验证后填写）
EOF
    echo "  ✅ README.md 已创建（模板）"
fi

# ---------- 步骤 5: _meta.yaml（总是更新，因为含时间戳）----------
echo "[5/6] 更新 _meta.yaml..."

META_FILE="${VERSION_DIR}/_meta.yaml"
COMPILE_DATE="$(date '+%Y-%m-%d')"

cat > "$META_FILE" <<EOF
software: ${SOFTWARE_NAME}
version: ${VERSION}
letter: ${FIRST_LETTER}
status: compiling
build_system: ${BUILD_SYSTEM}
compatibility: unknown
patches_count: $(find "${VERSION_DIR}/patches" -name "000*.patch" -type f 2>/dev/null | wc -l | tr -d ' ')
archive_path: archives/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}
compile_date: ${COMPILE_DATE}
EOF
echo "  ✅ _meta.yaml 已更新"

# ---------- 步骤 6: 验证 + 归档状态报告 ----------
echo "[6/6] 验证档案完整性..."

_validate_ok=true
for _item in manifest.yaml PROGRESS.md README.md patches reports packaging; do
    if [ -e "${VERSION_DIR}/${_item}" ]; then
        echo "  ✅ ${_item}"
    else
        echo "  ❌ ${_item} 缺失"
        _validate_ok=false
    fi
done

# 归档状态摘要
echo ""
echo "════════════════════════════"
if $_validate_ok; then
    # 统计已有内容
    _patch_count=$(find "${VERSION_DIR}/patches" -name "000*.patch" -type f 2>/dev/null | wc -l | tr -d ' ')
    _report_count=$(find "${VERSION_DIR}/reports" -name "*.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    _pkg_count=$(find "${VERSION_DIR}/packaging" -name "*.tar.gz" -o -name "install.sh" 2>/dev/null | wc -l | tr -d ' ')
    _tmp_count=$(find "${VERSION_DIR}" -maxdepth 2 -name "*.tmp" -type f 2>/dev/null | wc -l | tr -d ' ')
    
    echo "✅ 编译档案就绪！"
    echo "  📂 路径: ${VERSION_DIR}"
    echo "  📋 补丁: ${_patch_count} 个 | 报告: ${_report_count} 个 | 打包产物: ${_pkg_count} 个"
    if [ "$_tmp_count" -gt 0 ]; then
        echo "  ⚠️  残留临时文件: ${_tmp_count} 个（最终归档前由收口步骤统一清理）"
    fi
    echo "  📋 下一步: 开始 Phase 3 编译执行"
else
    echo "⚠️  档案存在，但部分文件缺失。"
    exit 3
fi
echo "════════════════════════════"

# 提示归档收口
echo ""
echo "💡 提示: 最终完成所有编译步骤后，请执行归档收口（清理+校验）:"
echo "   见 SKILL.md Step 5.5 或运行: ./scripts/finalize-archive.sh ${SOFTWARE_NAME} ${VERSION}"
