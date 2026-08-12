#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# knowledge_check.sh — 知识库质量门禁 (CI-safe, pure shell, no Python required)
#
# 用途: 在 CI pipeline 中拦截贡献者提交的低质量知识草稿和格式问题。
#       覆盖 graph validate (C4.5/C5/C10/C11/C12) 的核心拦截点。
#
# 用法:
#   bash ci/scripts/knowledge_check.sh [REPO_ROOT]
#
# 退出码:
#   0 = 所有检查通过
#   1 = 发现知识库质量问题
# ─────────────────────────────────────────────────────────────────────────────
set -u

REPO_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
GRAPH_DIR="${REPO_ROOT}/knowledge/graph"
DOC_DIR="${REPO_ROOT}/knowledge/doc"
ERRORS=0

if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; NC=''
fi

fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS + 1)); }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  知识库质量门禁 (knowledge_check)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ ! -d "${GRAPH_DIR}" ]; then
    echo "knowledge/graph/ 目录不存在，跳过"
    echo "KC_RESULT=pass: no_graph"; exit 0
fi

# 只统计标准正式条目 E###.kv（纯数字编号），排除 draft/非标准命名的文件
KV_COUNT=$(ls -1 "${GRAPH_DIR}"/E[0-9][0-9][0-9].kv 2>/dev/null | wc -l)
echo "  .kv 文件数: ${KV_COUNT}"

# ═══════════════════════════════════════════════════════════════
# KC1: 草稿泄漏检测 (C12)
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] KC1: 草稿泄漏检测..."

# KC1a: knowledge/graph/draft/ 目录不应存在
DRAFT_SUBDIR="${GRAPH_DIR}/draft"
if [ -d "${DRAFT_SUBDIR}" ]; then
    LEAKED=$(ls -1 "${DRAFT_SUBDIR}"/E*.kv 2>/dev/null | wc -l)
    if [ "${LEAKED}" -gt 0 ]; then
        fail "KC1a: knowledge/graph/draft/ 存在 ${LEAKED} 个 .kv — 草稿应在 knowledge/drafts/"
    fi
fi

# KC1b+1c: 用一次 grep 批量检测 draft:true 和 contributor_id
KC1_ERRS=$(grep -rl '^draft:[[:space:]]*true\|^contributor_id:' "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')

# KC1d: 文件名含 draft 的文件不应出现在正式目录
KC1_NAME_ERRS=$(ls -1 "${GRAPH_DIR}"/E[0-9]*draft*.kv 2>/dev/null | xargs -r -n1 basename 2>/dev/null | tr '\n' ' ' || true)
if [ -n "$KC1_NAME_ERRS" ]; then
    KC1_ERRS="${KC1_ERRS} filename_draft(${KC1_NAME_ERRS})"
fi

if [ -n "$KC1_ERRS" ]; then
    fail "KC1: 草稿字段泄漏:${KC1_ERRS}"
else
    ok "KC1: 草稿泄漏检测通过"
fi

# ═══════════════════════════════════════════════════════════════
# KC2: 模板占位符残留检测 (C10) — 批量 grep
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] KC2: 模板占位符残留检测..."

KC2_FAIL=""
# keyword1.*keyword2.*keyword3
HITS=$(grep -rl 'keyword1.*keyword2.*keyword3' "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')
[ -n "$HITS" ] && KC2_FAIL="${KC2_FAIL} keyword_default(${HITS})"

# category-name
HITS=$(grep -rl '^category:.*category-name' "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')
[ -n "$HITS" ] && KC2_FAIL="${KC2_FAIL} category_placeholder(${HITS})"

# root_cause with TODO/FIXME/待补充
HITS=$(grep -rl 'TODO\|FIXME\|待补充' "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')
[ -n "$HITS" ] && KC2_FAIL="${KC2_FAIL} todo_in_content(${HITS})"

if [ -n "$KC2_FAIL" ]; then
    fail "KC2: 模板占位符残留:${KC2_FAIL}"
else
    ok "KC2: 模板占位符残留检测通过"
fi

# ═══════════════════════════════════════════════════════════════
# KC3: rec_auto_fix 格式校验 (C11) — 批量 grep
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] KC3: rec_auto_fix 格式校验..."

# 检测管道符值 true|false
PIPE_HITS=$(grep -rn 'rec_auto_fix:.*true|false' "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | cut -d: -f1 | xargs -r -n1 basename | tr '\n' ' ')
if [ -n "$PIPE_HITS" ]; then
    fail "KC3: rec_auto_fix 含管道符:${PIPE_HITS}"
else
    ok "KC3: rec_auto_fix 格式校验通过"
fi

# ═══════════════════════════════════════════════════════════════
# KC4: 非标准字段检测 (C4.5) — 批量 grep
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] KC4: 非标准字段检测..."

KC4_FAIL=""
for field in software symptom solution pattern affected_versions; do
    HITS=$(grep -rl "^${field}:" "${GRAPH_DIR}"/E[0-9]*.kv 2>/dev/null | xargs -r -n1 basename 2>/dev/null | tr '\n' ' ' || true)
    [ -n "$HITS" ] && KC4_FAIL="${KC4_FAIL} ${field}(${HITS})"
done

if [ -n "$KC4_FAIL" ]; then
    fail "KC4: 非标准字段:${KC4_FAIL}"
else
    ok "KC4: 非标准字段检测通过"
fi

# ═══════════════════════════════════════════════════════════════
# KC5: index.tsv 行数一致性 (C2)
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] KC5: index.tsv 行数一致性..."

INDEX_FILE="${GRAPH_DIR}/index.tsv"
if [ -f "$INDEX_FILE" ]; then
    INDEX_ROWS=$(grep -c '^E[0-9]' "$INDEX_FILE" 2>/dev/null || echo 0)
    if [ "$INDEX_ROWS" -ne "$KV_COUNT" ]; then
        fail "KC5: index.tsv 行数(${INDEX_ROWS}) vs .kv(${KV_COUNT}) 不匹配"
    else
        ok "KC5: index.tsv 一致 (${INDEX_ROWS} = ${KV_COUNT})"
    fi
fi

# ═══════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Errors: ${ERRORS}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "KC_RESULT=$([ $ERRORS -eq 0 ] && echo 'pass' || echo 'fail')"
echo "KC_ERRORS=${ERRORS}"

if [ "${ERRORS}" -eq 0 ]; then
    exit 0
else
    exit 1
fi
