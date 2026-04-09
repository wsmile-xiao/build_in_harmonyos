#!/bin/bash
# ==============================================================================
# [Layer 1] validate-patch.sh - 补丁文件可应用性验证（全自动）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性验证）
# 入口: ./scripts/validate-patch.sh <补丁文件> [源码目录]
# 依赖: patch
# 调用者: refresh-patch.sh, AI / 用户
# ==============================================================================
# validate-patch.sh - 验证补丁文件是否可以正确应用
# 用法: ./validate-patch.sh <补丁文件> [源码目录]

set -e

PATCH_FILE="$1"
SOURCE_DIR="${2:-.}"

if [ -z "$PATCH_FILE" ]; then
    echo "用法: $0 <补丁文件> [源码目录]"
    echo "示例: $0 patches/0001-port-for-ohos.patch ./openssl-1.1.1w"
    exit 1
fi

if [ ! -f "$PATCH_FILE" ]; then
    echo "错误: 补丁文件不存在: $PATCH_FILE"
    exit 1
fi

cd "$SOURCE_DIR"

echo "验证补丁: $PATCH_FILE"
echo "源码目录: $(pwd)"
echo ""

# 检测补丁级别
detect_patch_level() {
    local patch_file="$1"
    local first_line=$(head -1 "$patch_file")
    
    if echo "$first_line" | grep -q "^diff -u -r a/"; then
        echo 1
    elif echo "$first_line" | grep -q "^diff -u -r \.\*/"; then
        echo 1
    else
        # 默认尝试 -p1
        echo 1
    fi
}

PATCH_LEVEL=$(detect_patch_level "$PATCH_FILE")
echo "检测到补丁级别: -p$PATCH_LEVEL"
echo ""

# 干运行验证
echo "=== 干运行验证 ==="
if patch --dry-run -p$PATCH_LEVEL < "$PATCH_FILE" 2>&1; then
    echo ""
    echo "✅ 补丁验证通过！可以安全应用。"
    echo ""
    echo "应用补丁命令:"
    echo "  patch -p$PATCH_LEVEL < $PATCH_FILE"
else
    echo ""
    echo "❌ 补丁验证失败！"
    echo ""
    echo "可能的原因："
    echo "1. 补丁级别不正确（尝试 -p0 或 -p2）"
    echo "2. 源码版本与补丁不匹配"
    echo "3. 补丁已经应用过"
    exit 1
fi