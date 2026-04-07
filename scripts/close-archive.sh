#!/bin/sh
# close-archive.sh - 关闭编译档案（Phase 4 收尾）
# 用法: ./close-archive.sh <软件名> <版本> <最终状态>
#   最终状态: success | partial | failed
#
# Phase 4 归档收尾脚本。更新 manifest.yaml、_meta.yaml 和 PROGRESS.md，
# 将档案状态从 compiling 更新为最终状态。

set -e

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVES_DIR="${PROJECT_DIR}/archives"

show_help() {
    cat <<'HELPEOF'
用法:
  ./close-archive.sh <软件名> <版本> <最终状态>

描述:
  关闭编译档案（Phase 4 收尾），执行以下操作：
  1. 更新 manifest.yaml 中的 status 字段
  2. 更新 _meta.yaml 中对应条目的 status、compile_date、compatibility
  3. 在 PROGRESS.md 末尾追加编译结束时间戳和最终状态
  4. 提示用户运行 gen_summary.py
  5. 检查 PROGRESS.md 中是否有 ⏳ 待评估的知识条目，如果有则警告

参数:
  <软件名>      软件名称
  <版本>        版本号
  <最终状态>    编译结果：success（成功）/ partial（部分成功）/ failed（失败）

示例:
  ./close-archive.sh openssl 3.0.1 success
  ./close-archive.sh zlib 1.2.13 partial
  ./close-archive.sh libfoo 2.0 failed

退出码:
  0  成功
  1  参数错误
  2  档案不存在
  3  更新失败
  4  存在未评估的知识条目（警告，仍成功关闭）
HELPEOF
    exit 0
}

# ---------- 参数检查 ----------
if [ $# -lt 3 ]; then
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
STATUS="$3"

# 验证状态参数
case "$STATUS" in
    success)
        STATUS_DISPLAY="✅ 编译成功"
        STATUS_EMOJI="✅ 成功"
        ;;
    partial)
        STATUS_DISPLAY="⚠️  部分成功"
        STATUS_EMOJI="⚠️  部分成功"
        ;;
    failed)
        STATUS_DISPLAY="❌ 编译失败"
        STATUS_EMOJI="❌ 失败"
        ;;
    *)
        echo "❌ 无效的最终状态: $STATUS"
        echo "   有效值: success | partial | failed"
        exit 1
        ;;
esac

# ---------- 计算路径 ----------
FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"
VERSION_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}"
MANIFEST_FILE="${VERSION_DIR}/manifest.yaml"
PROGRESS_FILE="${VERSION_DIR}/PROGRESS.md"

echo "📝 关闭编译档案"
echo "  软件:   ${SOFTWARE_NAME}"
echo "  版本:   ${VERSION}"
echo "  状态:   ${STATUS_DISPLAY}"
echo "  路径:   ${VERSION_DIR}"
echo ""

# ---------- 检查档案是否存在 ----------
if [ ! -d "$VERSION_DIR" ]; then
    echo "❌ 档案目录不存在: $VERSION_DIR"
    exit 2
fi

if [ ! -f "$MANIFEST_FILE" ]; then
    echo "❌ manifest.yaml 不存在: $MANIFEST_FILE"
    exit 2
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "❌ PROGRESS.md 不存在: $PROGRESS_FILE"
    exit 2
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"

# ---------- 步骤 0: 补丁管线（自动触发） ----------
echo "[0/6] 检查补丁状态..."

PATCH_DIR="${VERSION_DIR}/patches"
_PATCH_EXISTS=0
if [ -d "$PATCH_DIR" ]; then
    _PATCH_COUNT=$(find "$PATCH_DIR" -name "000*.patch" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$_PATCH_COUNT" -gt 0 ]; then
        _PATCH_EXISTS=1
        echo "  ✅ 已有 ${_PATCH_COUNT} 个补丁文件"
    else
        echo "  ⚠️  patches/ 目录存在但无补丁文件"
    fi
else
    echo "  ⚠️  patches/ 目录不存在"
fi

if [ "$_PATCH_EXISTS" -eq 0 ] && [ "$STATUS" != "failed" ]; then
    # 检查是否已被 finish-build.sh 的 Step [1/3] 调用过
    if [ "${_SKIP_PATCH_GENERATION:-false}" = "true" ]; then
        echo "  ⏭️  补丁管线已由 finish-build.sh 执行，跳过"
    else
        echo ""
        echo "  🔄 自动触发补丁管线..."
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        if "$SCRIPT_DIR/refresh-patch.sh" --auto "$SOFTWARE_NAME" "$VERSION"; then
            echo "  ✅ 补丁管线完成"
        else
            echo "  ⚠️  补丁管线失败（退出码 $?），继续关闭档案"
            echo "     可稍后手动执行: ./scripts/refresh-patch.sh --auto ${SOFTWARE_NAME} ${VERSION}"
        fi
    fi
elif [ "$_PATCH_EXISTS" -eq 0 ] && [ "$STATUS" = "failed" ]; then
    echo "  ➖ 编译失败，跳过补丁生成"
fi

# ---------- 步骤 1: 更新 manifest.yaml ----------
echo "[1/6] 更新 manifest.yaml..."
# 使用 sed 替换 status 行
if sed -i "s/^status: compiling/status: ${STATUS}/" "$MANIFEST_FILE" 2>/dev/null; then
    echo "  ✅ status 已更新为: ${STATUS}"
else
    # macOS 兼容：sed -i 需要备份后缀
    if sed -i '' "s/^status: compiling/status: ${STATUS}/" "$MANIFEST_FILE" 2>/dev/null; then
        echo "  ✅ status 已更新为: ${STATUS}"
    else
        # 回退方案：直接创建临时文件
        _tmp_manifest="${MANIFEST_FILE}.tmp"
        sed "s/^status: compiling/status: ${STATUS}/" "$MANIFEST_FILE" > "$_tmp_manifest" && mv "$_tmp_manifest" "$MANIFEST_FILE"
        if grep -q "^status: ${STATUS}" "$MANIFEST_FILE"; then
            echo "  ✅ status 已更新为: ${STATUS}"
        else
            echo "  ❌ status 更新失败"
            exit 3
        fi
    fi
fi

# ---------- 步骤 2: 更新 _meta.yaml ----------
echo "[2/6] 更新 _meta.yaml..."
META_FILE="${VERSION_DIR}/_meta.yaml"

if [ -f "$META_FILE" ]; then
    # 更新 status
    _tmp_meta="${META_FILE}.tmp"
    sed "s/^status: compiling/status: ${STATUS}/" "$META_FILE" > "$_tmp_meta" && mv "$_tmp_meta" "$META_FILE"
    echo "  ✅ _meta.yaml status 已更新为: ${STATUS}"

    # 更新 compile_date
    COMPILE_DATE="$(date '+%Y-%m-%d')"
    if grep -q "^compile_date:" "$META_FILE"; then
        _tmp_meta="${META_FILE}.tmp"
        sed "s/^compile_date:.*/compile_date: ${COMPILE_DATE}/" "$META_FILE" > "$_tmp_meta" && mv "$_tmp_meta" "$META_FILE"
    fi

    # 从 manifest.yaml 提取 compatibility level
    _compat_level=$(grep -A1 '^compatibility:' "$MANIFEST_FILE" | grep 'level:' | head -1 | sed 's/.*level: *//')
    if [ -n "$_compat_level" ]; then
        _tmp_meta="${META_FILE}.tmp"
        sed "s/^compatibility:.*/compatibility: ${_compat_level}/" "$META_FILE" > "$_tmp_meta" && mv "$_tmp_meta" "$META_FILE"
        echo "  ✅ _meta.yaml compatibility 已更新为: ${_compat_level}"
    fi

    # 更新 patches_count（从 manifest.yaml 的 patches_applied 计算）
    _patches_count=$(grep -c 'purpose:' "$MANIFEST_FILE" 2>/dev/null || echo 0)
    _patches_count=$(echo "$_patches_count" | tr -d ' ')
    if grep -q "^patches_count:" "$META_FILE"; then
        _tmp_meta="${META_FILE}.tmp"
        sed "s/^patches_count:.*/patches_count: ${_patches_count}/" "$META_FILE" > "$_tmp_meta" && mv "$_tmp_meta" "$META_FILE"
    fi
else
    echo "  ⚠️  _meta.yaml 不存在，跳过更新"
fi

# ---------- 步骤 3: 更新 PROGRESS.md ----------
echo "[3/6] 更新 PROGRESS.md..."

cat >> "$PROGRESS_FILE" <<EOF

---

## 编译结束

- **结束时间**: ${TIMESTAMP}
- **最终状态**: ${STATUS_DISPLAY}
- **关闭操作**: 由 ${SCRIPT_NAME} 执行

EOF

if [ -f "$PROGRESS_FILE" ]; then
    echo "  ✅ PROGRESS.md 已更新"
else
    echo "  ❌ PROGRESS.md 更新失败"
    exit 3
fi

# ---------- 步骤 4: 提示运行 gen_summary.py ----------
echo "[4/6] 后续建议..."
echo "  📋 建议运行: python3 scripts/gen_summary.py"
echo "     生成编译总结报告。"

# ---------- 步骤 5: 检查待评估知识条目 ----------
echo "[5/6] 检查知识条目..."

_pending_count=$(grep -c '⏳\|待评估\|TODO\|FIXME' "$PROGRESS_FILE" 2>/dev/null || echo 0)
_pending_count=$(echo "$_pending_count" | tr -d ' ')

if [ "$_pending_count" -gt 0 ]; then
    echo "  ⚠️  发现 ${_pending_count} 个待评估条目:"
    grep -n '⏳\|待评估\|TODO\|FIXME' "$PROGRESS_FILE" 2>/dev/null | while IFS=: read -r _ln _content; do
        echo "     行 ${_ln}: ${_content}"
    done
    echo ""
    echo "  ⚠️  建议在归档前处理这些待评估条目"
else
    echo "  ✅ 无待评估知识条目"
fi

# ---------- 完成摘要 ----------
echo ""
echo "════════════════════════════"
echo "✅ 编译档案已关闭"
echo "  📦 软件: ${SOFTWARE_NAME} ${VERSION}"
echo "  📊 状态: ${STATUS_DISPLAY}"
echo "  📂 路径: ${VERSION_DIR}"
if [ "$_pending_count" -gt 0 ]; then
    echo "  ⚠️  有 ${_pending_count} 个待评估条目"
    exit 4
fi
echo "════════════════════════════"
