#!/bin/sh
# ==============================================================================
# [Layer 3] restore-session.sh - 编译会话恢复工具（AI 主导）
# ==============================================================================
# 层级: L3(辅助工具)
# 决策点: AI主导（恢复后需 AI 判断下一步操作）
# 入口: ./scripts/restore-session.sh <软件名> <版本>
# 依赖: PROGRESS.md, manifest.yaml
# 调用者: AI / 用户（会话中断后恢复上下文）
# ==============================================================================
# restore-session.sh - 会话恢复（上下文压缩后执行）
# 用法：./scripts/restore-session.sh <软件名> <版本>
# 从 PROGRESS.md 和 manifest.yaml 恢复编译上下文

set -e

NAME="$1"
VERSION="$2"
[ -z "$NAME" ] || [ -z "$VERSION" ] && {
    echo "用法: ./scripts/restore-session.sh <软件名> <版本>"
    echo "示例: ./scripts/restore-session.sh curl 8.7.1"
    exit 1
}

# 查找档案目录
LETTER=$(echo "$NAME" | cut -c1)
ARCHIVE="archives/${LETTER}/${NAME}/${VERSION}"

if [ ! -f "$ARCHIVE/PROGRESS.md" ]; then
    echo "❌ 未找到 $ARCHIVE/PROGRESS.md"
    exit 1
fi

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "========================================"
echo "📋 会话恢复 - $NAME $VERSION"
echo "========================================"
echo ""

# 1. 当前状态
echo "## 当前状态"
STATUS=$(grep '当前状态' "$ARCHIVE/PROGRESS.md" | head -1 | sed 's/.*：//' || echo "未知")
echo "  阶段: $STATUS"

# 2. manifest.yaml 关键信息
echo ""
echo "## 档案信息"
if [ -f "$ARCHIVE/manifest.yaml" ]; then
    BUILD_SYS=$(grep '^build_system:' "$ARCHIVE/manifest.yaml" | sed 's/build_system: *//')
    DEPS=$(grep -A5 '^dependencies:' "$ARCHIVE/manifest.yaml" | grep 'required:' | head -1 || echo "无")
    echo "  构建系统: $BUILD_SYS"
    echo "  必需依赖: $DEPS"
fi

# 3. 待办事项
echo ""
echo "## 待办事项"
TODO=$(grep -A 20 '## 待办' "$ARCHIVE/PROGRESS.md" | grep '\- \[ \]' || echo "  无待办")
echo "$TODO"

# 4. 遗忘约束速查
echo ""
echo "## ⚠️ 致命约束速查"
echo "  D1: diff -ruN original/ modified/ 校验补丁完整性"
echo "  D2: Phase 4 Step 6 是校验+补充，不是全量复盘"
echo "  D3: 归档后运行 aggregate-index.sh + gen_summary.py"
echo "  D5: make check 前运行 prep-test.sh"
echo "  D6: 清理临时文件"
echo "  D7: 四维度完成度（编译+补丁+知识+索引）"
echo ""
echo "  📖 详细约束请重新读取 KNOW_YOUR_WHY.md"

# 5. 工具速查
echo ""
echo "## 🔧 下一步工具"
echo "  环境检查: ./scripts/check-env.sh"
echo "  构建检测: ./scripts/detect-build-system.sh <源码目录>"
echo "  测试准备: ./scripts/prep-test.sh"
echo "  知识校验: ./scripts/check-knowledge-gap.sh $NAME $VERSION"
echo "  归档收尾: ./scripts/close-archive.sh $NAME $VERSION success"

echo ""
echo "========================================"
echo "✅ 上下文已恢复。继续编译任务。"
echo "========================================"
