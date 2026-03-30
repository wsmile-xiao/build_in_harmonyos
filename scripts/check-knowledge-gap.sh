#!/bin/sh
# check-knowledge-gap.sh - 检查知识库中的遗漏（Phase 4 Step 6 自动化辅助）
# 用法: ./check-knowledge-gap.sh <软件名> <版本>
#
# 读取 PROGRESS.md 和 manifest.yaml，检查知识提取是否完整，
# 确保编译过程中的发现都已正确记录和关联。

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVES_DIR="${PROJECT_DIR}/archives"

show_help() {
    cat <<'HELPEOF'
用法:
  ./check-knowledge-gap.sh <软件名> <版本>

描述:
  检查知识库中的遗漏（Phase 4 Step 6 自动化辅助）。
  扫描编译档案中的知识条目，验证知识提取完整性。

  检查项目：
  1. 读取 PROGRESS.md，提取所有"发现"条目
  2. 检查每个条目的「知识提取状态」是否标记为已完成
  3. 检查 manifest.yaml 的 knowledge_gained 列表
  4. 验证 knowledge_gained 条目是否包含 knowledge_ref 引用
  5. 输出完整的校验报告

  PROGRESS.md 中知识条目格式约定：
    - ✅ 已提取的知识条目
    - ⏳ 待提取的知识条目
    - ❌ 提取失败的知识条目

参数:
  <软件名>    软件名称
  <版本>      版本号

示例:
  ./check-knowledge-gap.sh openssl 3.0.1
  ./check-knowledge-gap.sh zlib 1.2.13

退出码:
  0  所有知识条目已完整提取
  1  参数错误
  2  档案不存在
  3  存在知识遗漏（需要补充）
HELPEOF
    exit 0
}

# ---------- 初始化计数器 ----------
total_entries=0
extracted_entries=0
pending_entries=0
failed_entries=0
unreferenced_knowledge=0

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

# ---------- 计算路径 ----------
FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"
VERSION_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}/${VERSION}"
MANIFEST_FILE="${VERSION_DIR}/manifest.yaml"
PROGRESS_FILE="${VERSION_DIR}/PROGRESS.md"

echo "🔍 知识库校验"
echo "  软件: ${SOFTWARE_NAME}"
echo "  版本: ${VERSION}"
echo "  路径: ${VERSION_DIR}"
echo ""

# ---------- 检查档案是否存在 ----------
if [ ! -d "$VERSION_DIR" ]; then
    echo "❌ 档案目录不存在: $VERSION_DIR"
    exit 2
fi

# ---------- 步骤 1: 扫描 PROGRESS.md 中的发现条目 ----------
echo "[1/4] 扫描 PROGRESS.md 知识条目..."

TMP_REPORT="/tmp/knowledge_check_$$.txt"
: > "$TMP_REPORT"

if [ -f "$PROGRESS_FILE" ]; then
    # 提取"发现与知识"部分
    _in_knowledge=false
    _entry_num=0

    while IFS= read -r _line; do
        # 检测进入"发现与知识"章节
        case "$_line" in
            *"发现与知识"*|*"知识积累"*|*" discoveries "*|*" findings "*)
                _in_knowledge=true
                continue
                ;;
            *"## "*|"---")
                if $_in_knowledge; then
                    _in_knowledge=false
                fi
                continue
                ;;
        esac

        if $_in_knowledge; then
            # 跳过空行和注释
            case "$_line" in
                ""|"<!--"*|"-->")
                    continue
                    ;;
            esac

            # 检查知识条目标记
            case "$_line" in
                *"✅"*)
                    _entry_num=$(( _entry_num + 1 ))
                    extracted_entries=$(( extracted_entries + 1 ))
                    echo "OK:${_entry_num}:${_line}" >> "$TMP_REPORT"
                    ;;
                *"⏳"*|*"TODO"*|*"待评估"*|*"待提取"*)
                    _entry_num=$(( _entry_num + 1 ))
                    pending_entries=$(( pending_entries + 1 ))
                    echo "PENDING:${_entry_num}:${_line}" >> "$TMP_REPORT"
                    ;;
                *"❌"*)
                    _entry_num=$(( _entry_num + 1 ))
                    failed_entries=$(( failed_entries + 1 ))
                    echo "FAILED:${_entry_num}:${_line}" >> "$TMP_REPORT"
                    ;;
                *"- "*|*"* "*)
                    # 可能的知识条目（无明确标记）
                    _entry_num=$(( _entry_num + 1 ))
                    pending_entries=$(( pending_entries + 1 ))
                    echo "PENDING:${_entry_num}:${_line}" >> "$TMP_REPORT"
                    ;;
            esac
        fi
    done < "$PROGRESS_FILE"

    total_entries=$(( extracted_entries + pending_entries + failed_entries ))

    echo "  📊 发现 ${total_entries} 个知识条目:"
    if [ "$extracted_entries" -gt 0 ]; then
        echo "     ✅ 已提取: ${extracted_entries}"
    fi
    if [ "$pending_entries" -gt 0 ]; then
        echo "     ⏳ 待提取: ${pending_entries}"
    fi
    if [ "$failed_entries" -gt 0 ]; then
        echo "     ❌ 提取失败: ${failed_entries}"
    fi
    if [ "$total_entries" -eq 0 ]; then
        echo "     ℹ️  未发现知识条目"
    fi
else
    echo "  ⚠️  PROGRESS.md 不存在，跳过知识条目扫描"
fi

echo ""

# ---------- 步骤 2: 检查待提取条目详情 ----------
echo "[2/4] 检查待提取条目详情..."

if [ "$pending_entries" -gt 0 ]; then
    grep '^PENDING:' "$TMP_REPORT" 2>/dev/null | while IFS=: read -r _status _num _content; do
        echo "  ⏳ #${_num}: ${_content}" | sed 's/^[[:space:]]*//'
    done
elif [ "$total_entries" -gt 0 ]; then
    echo "  ✅ 所有知识条目已提取"
fi

echo ""

# ---------- 步骤 3: 检查 manifest.yaml 中的 knowledge_gained ----------
echo "[3/4] 检查 manifest.yaml knowledge_gained..."

_knowledge_count=0
_knowledge_with_ref=0

if [ -f "$MANIFEST_FILE" ]; then
    _in_knowledge=false

    while IFS= read -r _line; do
        case "$_line" in
            "knowledge_gained:"*"["|"- "*)
                case "$_line" in
                    "knowledge_gained:"*"[]")
                        # 空列表
                        ;;
                    "knowledge_gained:"*"["*)
                        _in_knowledge=true
                        ;;
                    "- "*)
                        if $_in_knowledge; then
                            _knowledge_count=$(( _knowledge_count + 1 ))
                            case "$_line" in
                                *"knowledge_ref"*|*"ref:"*|*"reference:"*)
                                    _knowledge_with_ref=$(( _knowledge_with_ref + 1 ))
                                    ;;
                                *)
                                    unreferenced_knowledge=$(( unreferenced_knowledge + 1 ))
                                    echo "  ⚠️  无引用: ${_line}"
                                    ;;
                            esac
                        fi
                        ;;
                esac
                ;;
            *"]"*)
                if $_in_knowledge; then
                    _in_knowledge=false
                fi
                ;;
        esac
    done < "$MANIFEST_FILE"

    echo "  📊 knowledge_gained 条目: ${_knowledge_count}"
    if [ "$_knowledge_count" -gt 0 ]; then
        echo "     有引用: ${_knowledge_with_ref}"
        if [ "$unreferenced_knowledge" -gt 0 ]; then
            echo "     ⚠️  无引用: ${unreferenced_knowledge}"
        fi
    fi
    if [ "$_knowledge_count" -eq 0 ]; then
        echo "  ℹ️  knowledge_gained 为空"
    fi
else
    echo "  ⚠️  manifest.yaml 不存在，跳过检查"
fi

echo ""

# ---------- 步骤 4: 输出校验报告 ----------
echo "[4/4] 生成校验报告..."

echo "════════════════════════════"
echo "📊 知识库校验报告"
echo "════════════════════════════"
echo ""
echo "📦 软件版本: ${SOFTWARE_NAME} ${VERSION}"
echo ""
echo "📖 PROGRESS.md 知识条目:"
echo "   总计:     ${total_entries}"
echo "   ✅ 已提取: ${extracted_entries}"
echo "   ⏳ 待提取: ${pending_entries}"
echo "   ❌ 失败:   ${failed_entries}"
echo ""
echo "📋 manifest.yaml knowledge_gained:"
echo "   条目总数: ${_knowledge_count}"
echo "   有引用:   ${_knowledge_with_ref}"
echo "   无引用:   ${unreferenced_knowledge}"
echo ""

# ---------- 综合判断 ----------
_has_gap=false

if [ "$pending_entries" -gt 0 ]; then
    echo "⚠️  发现 ${pending_entries} 个待提取知识条目"
    _has_gap=true
fi

if [ "$failed_entries" -gt 0 ]; then
    echo "❌ 发现 ${failed_entries} 个提取失败的知识条目"
    _has_gap=true
fi

if [ "$unreferenced_knowledge" -gt 0 ]; then
    echo "⚠️  发现 ${unreferenced_knowledge} 个未关联引用的 knowledge_gained 条目"
    _has_gap=true
fi

if $_has_gap; then
    echo ""
    echo "⚠️  知识库存在遗漏，建议补充后再归档"
    echo "════════════════════════════"
    rm -f "$TMP_REPORT"
    exit 3
else
    echo "✅ 知识库校验通过，无遗漏"
    echo "════════════════════════════"
    rm -f "$TMP_REPORT"
    exit 0
fi
