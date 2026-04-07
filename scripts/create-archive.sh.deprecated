#!/bin/bash
# create-archive.sh - 为编译成功的软件创建标准档案结构
# 用法: ./create-archive.sh <软件名> <版本> [源码目录]

set -e

SOFTWARE="$1"
VERSION="$2"
SOURCE_DIR="${3:-.}"
BASE_DIR="$(dirname "$0")/.."

if [ -z "$SOFTWARE" ] || [ -z "$VERSION" ]; then
    echo "用法: $0 <软件名> <版本> [源码目录]"
    echo "示例: $0 openssl 1.1.1w ./openssl-1.1.1w"
    exit 1
fi

# 获取首字母
FIRST_LETTER=$(echo "$SOFTWARE" | cut -c1 | tr '[:upper:]' '[:lower:]')

# 创建档案目录
ARCHIVE_DIR="$BASE_DIR/archives/$FIRST_LETTER/$SOFTWARE/$VERSION"
mkdir -p "$ARCHIVE_DIR"/{patches,reports,scripts,logs}

echo "创建档案目录: $ARCHIVE_DIR"

# 复制 manifest 模板
if [ ! -f "$ARCHIVE_DIR/manifest.yaml" ]; then
    cp "$BASE_DIR/templates/manifest.yaml" "$ARCHIVE_DIR/"
    echo "创建 manifest.yaml 模板"
fi

# 复制 README 模板
if [ ! -f "$ARCHIVE_DIR/README.md" ]; then
    cp "$BASE_DIR/templates/README.md" "$ARCHIVE_DIR/"
    echo "创建 README.md 模板"
fi

# 生成补丁（如果源码目录存在）
if [ -d "$SOURCE_DIR" ] && [ -d "$SOURCE_DIR.orig" ]; then
    echo "检测到 orig 目录，生成补丁..."
    PATCH_FILE="$ARCHIVE_DIR/patches/0001-port-for-ohos.patch"
    diff -u -r "$SOURCE_DIR.orig" "$SOURCE_DIR" > "$PATCH_FILE" 2>/dev/null || true
    if [ -s "$PATCH_FILE" ]; then
        echo "补丁已生成: $PATCH_FILE"
    else
        rm -f "$PATCH_FILE"
        echo "没有检测到修改，跳过补丁生成"
    fi
fi

# 更新索引
echo ""
echo "档案创建完成！"
echo ""
echo "下一步操作："
echo "1. 编辑 $ARCHIVE_DIR/manifest.yaml 填写元数据"
echo "2. 编辑 $ARCHIVE_DIR/README.md 编写编译说明"
echo "3. 如有测试报告，放入 $ARCHIVE_DIR/reports/"
echo "4. 更新 $BASE_DIR/archives/_index.yaml 添加索引"