#!/bin/sh
# init-archive.sh - 创建编译档案骨架（Phase 1.5）
# 用法: ./init-archive.sh <软件名> <版本> [源码下载URL] [构建系统类型]
#
# 在 archives/ 目录下创建完整的软件编译档案目录结构，
# 包括 manifest.yaml、PROGRESS.md 和必要的子目录。

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
  创建编译档案骨架（Phase 1.5），包括：
  - 目录结构：archives/{letter}/{name}/{version}/{patches,reports,scripts,logs}
  - manifest.yaml（编译元数据）
  - PROGRESS.md（编译进度跟踪）
  - 创建 _meta.yaml 索引元数据

参数:
  <软件名>          软件名称（如 openssl, zlib, curl）
  <版本>            版本号（如 3.0.1, 1.2.13）
  [源码下载URL]     源码下载地址（可选）
  [构建系统类型]    构建系统类型：cmake|autotools|meson|make|custom（可选，默认 unknown）

示例:
  ./init-archive.sh openssl 3.0.1 https://www.openssl.org/source/openssl-3.0.1.tar.gz
  ./init-archive.sh zlib 1.2.13 https://zlib.net/zlib-1.2.13.tar.gz cmake
  ./init-archive.sh libfoo 2.0

退出码:
  0  成功
  1  参数错误
  2  目录创建失败
  3  模板创建失败
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

# ---------- 计算首字母 ----------
FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"

# ---------- 构建路径 ----------
SOFTWARE_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}"
VERSION_DIR="${SOFTWARE_DIR}/${VERSION}"

echo "📝 创建编译档案骨架"
echo "  软件:   ${SOFTWARE_NAME}"
echo "  版本:   ${VERSION}"
echo "  构建:   ${BUILD_SYSTEM}"
if [ -n "$SOURCE_URL" ]; then
    echo "  源码:   ${SOURCE_URL}"
fi
echo "  路径:   ${VERSION_DIR}"
echo ""

# ---------- 步骤 1: 创建目录结构 ----------
echo "[1/5] 创建目录结构..."

SUBDIRS="patches reports scripts logs"
for subdir in $SUBDIRS; do
    _target="${VERSION_DIR}/${subdir}"
    if mkdir -p "$_target"; then
        echo "  ✅ ${subdir}/"
    else
        echo "  ❌ 创建目录失败: ${subdir}/"
        exit 2
    fi
done

# ---------- 步骤 2: 创建 manifest.yaml ----------
echo "[2/5] 创建 manifest.yaml..."

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

cat > "${VERSION_DIR}/manifest.yaml" <<EOF
# 编译档案 manifest
# 由 init-archive.sh 自动生成
# 生成时间: ${TIMESTAMP}

software: ${SOFTWARE_NAME}
version: ${VERSION}
status: compiling

build_system: ${BUILD_SYSTEM}
EOF

if [ -n "$SOURCE_URL" ]; then
    cat >> "${VERSION_DIR}/manifest.yaml" <<EOF
source_url: ${SOURCE_URL}
EOF
fi

cat >> "${VERSION_DIR}/manifest.yaml" <<EOF

# 编译环境信息
created_at: ${TIMESTAMP}

# 知识积累
knowledge_gained: []

# 补丁列表
patches_applied: []

# 编译日志
build_log: logs/build.log
EOF

if [ -f "${VERSION_DIR}/manifest.yaml" ]; then
    echo "  ✅ manifest.yaml 已创建"
else
    echo "  ❌ manifest.yaml 创建失败"
    exit 3
fi

# ---------- 步骤 3: 创建 PROGRESS.md ----------
echo "[3/5] 创建 PROGRESS.md..."

SOURCE_PATH=""
if [ -n "$SOURCE_URL" ]; then
    SOURCE_PATH="${SOURCE_URL}"
fi

cat > "${VERSION_DIR}/PROGRESS.md" <<EOF
# ${SOFTWARE_NAME} ${VERSION} — 编译进度

> 档案创建时间: ${TIMESTAMP}

## 基本信息

| 项目 | 值 |
|------|-----|
| 软件 | ${SOFTWARE_NAME} |
| 版本 | ${VERSION} |
| 状态 | 🔵 编译中 |
| 构建系统 | ${BUILD_SYSTEM} |
EOF

if [ -n "$SOURCE_PATH" ]; then
    cat >> "${VERSION_DIR}/PROGRESS.md" <<EOF
| 源码路径 | ${SOURCE_PATH} |
EOF
fi

cat >> "${VERSION_DIR}/PROGRESS.md" <<'EOF'

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

EOF

if [ -f "${VERSION_DIR}/PROGRESS.md" ]; then
    echo "  ✅ PROGRESS.md 已创建"
else
    echo "  ❌ PROGRESS.md 创建失败"
    exit 3
fi

# ---------- 步骤 4: 创建 _meta.yaml ----------
echo "[4/5] 创建 _meta.yaml..."

META_FILE="${VERSION_DIR}/_meta.yaml"
COMPILE_DATE="$(date '+%Y-%m-%d')"

cat > "$META_FILE" <<EOF
software: ${SOFTWARE_NAME}
version: ${VERSION}
letter: ${FIRST_LETTER}
status: compiling
build_system: ${BUILD_SYSTEM}
compatibility: unknown
patches_count: 0
archive_path: archives/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}
compile_date: ${COMPILE_DATE}
EOF

if [ -f "$META_FILE" ]; then
    echo "  ✅ _meta.yaml 已创建"
else
    echo "  ❌ _meta.yaml 创建失败"
    exit 3
fi

echo "  ℹ️  不再修改 _index.yaml，请使用 aggregate-index.sh 在 main 分支生成"

# ---------- 步骤 5: 验证 ----------
echo "[5/5] 验证档案完整性..."

_validate_ok=true
for _item in manifest.yaml PROGRESS.md patches reports scripts logs; do
    if [ -e "${VERSION_DIR}/${_item}" ]; then
        echo "  ✅ ${_item}"
    else
        echo "  ❌ ${_item} 缺失"
        _validate_ok=false
    fi
done

echo ""
if $_validate_ok; then
    echo "════════════════════════════"
    echo "✅ 编译档案骨架创建成功！"
    echo "  📂 路径: ${VERSION_DIR}"
    echo "  📋 下一步: 下载源码，开始 Phase 1 编译"
    echo "════════════════════════════"
else
    echo "⚠️  档案创建完成，但部分文件验证失败。"
    exit 3
fi
