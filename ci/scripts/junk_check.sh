#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# junk_check.sh — 杂项文件拦截 (CI-safe, pure shell)
#
# 用途: 拦截贡献者提交不应纳入版本控制的文件
#       （运行时状态、二进制产物、打包临时文件等）
#
# 用法:
#   bash ci/scripts/junk_check.sh [REPO_ROOT]
#
# 退出码:
#   0 = 未发现杂项文件
#   1 = 发现杂项文件
# ─────────────────────────────────────────────────────────────────────────────
set -u

REPO_ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
ERRORS=0

if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; NC='\033[0m'
else
    RED=''; GREEN=''; NC=''
fi

fail() { echo -e "${RED}[FAIL]${NC} $1"; ERRORS=$((ERRORS + 1)); }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  杂项文件拦截 (junk_check)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 确定检查范围 ──
# CI PR 模式：只检查当前 PR 新增/修改的文件（git diff origin/main...HEAD）
# Full/Release 模式：检查整个仓库（无 origin/main 或 diff 为空时回退）
JUNK_CHECK_MODE="incremental"

if git -C "${REPO_ROOT}" rev-parse --verify origin/main >/dev/null 2>&1; then
    CHECK_FILES=$(git -C "${REPO_ROOT}" diff --name-only --diff-filter=ACMR origin/main...HEAD 2>/dev/null || true)
    if [ -z "$CHECK_FILES" ]; then
        JUNK_CHECK_MODE="full"
        CHECK_FILES=$(git -C "${REPO_ROOT}" ls-files 2>/dev/null || true)
    fi
else
    JUNK_CHECK_MODE="full"
    CHECK_FILES=$(git -C "${REPO_ROOT}" ls-files 2>/dev/null || true)
fi

if [ -z "$CHECK_FILES" ]; then
    echo "  非 git 仓库或无文件变更，跳过"
    echo "JC_RESULT=pass: empty"; exit 0
fi

FILE_COUNT=$(echo "$CHECK_FILES" | wc -l)
echo "  检查模式: ${JUNK_CHECK_MODE} (${FILE_COUNT} 个文件)"

# ═══════════════════════════════════════════════════════════════
# JC1: 运行时状态文件
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC1: 运行时状态文件检测..."

JC1_HITS=""
HITS=$(echo "$CHECK_FILES" | grep -E '\.submit-state\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.handoff\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.ci-result\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.build-status\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '/ci-metadata\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '/\.(staging-|build-closed|conan-verified|built|configured|installed|patched|tested|unpack|verify-passed)' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
# .packaged 状态文件（排除 packaging/ 目录下的同名路径）
HITS=$(echo "$CHECK_FILES" | grep -E '/\.packaged$' | grep -v '/packaging/\.packaged$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

if [ -n "$(echo "$JC1_HITS" | tr -d '[:space:]')" ]; then
    JC1_COUNT=$(echo -e "$JC1_HITS" | grep -c . || true)
    fail "JC1: ${JC1_COUNT} 个运行时状态文件被跟踪:"
    echo -e "$JC1_HITS" | head -10 | sed 's/^/       /'
    [ "$JC1_COUNT" -gt 10 ] && echo "       ... (共 ${JC1_COUNT} 个)"
fi

# ═══════════════════════════════════════════════════════════════
# JC2: 二进制产物
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC2: 二进制产物检测..."

JC2_HITS=""
HITS=$(echo "$CHECK_FILES" | grep -E '\.a$' || true)
JC2_HITS="${JC2_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.so($|\.)' || true)
JC2_HITS="${JC2_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.o$' || true)
JC2_HITS="${JC2_HITS}${HITS:+\n$HITS}"

if [ -n "$(echo "$JC2_HITS" | tr -d '[:space:]')" ]; then
    JC2_COUNT=$(echo -e "$JC2_HITS" | grep -c . || true)
    fail "JC2: ${JC2_COUNT} 个二进制产物被跟踪:"
    echo -e "$JC2_HITS" | head -10 | sed 's/^/       /'
fi

# ═══════════════════════════════════════════════════════════════
# JC3: 源码 tarball / 打包产物
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC3: 源码 tarball / 打包产物检测..."

JC3_HITS=""
HITS=$(echo "$CHECK_FILES" | grep -E '^sources/' || true)
JC3_HITS="${JC3_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.tar\.(gz|xz|bz2|tgz)$' | grep -v 'prebuilt' || true)
JC3_HITS="${JC3_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '/packaging/.*\.tar' || true)
JC3_HITS="${JC3_HITS}${HITS:+\n$HITS}"

if [ -n "$(echo "$JC3_HITS" | tr -d '[:space:]')" ]; then
    JC3_COUNT=$(echo -e "$JC3_HITS" | grep -c . || true)
    fail "JC3: ${JC3_COUNT} 个 tarball/打包产物被跟踪:"
    echo -e "$JC3_HITS" | head -10 | sed 's/^/       /'
    [ "$JC3_COUNT" -gt 10 ] && echo "       ... (共 ${JC3_COUNT} 个)"
fi

# ═══════════════════════════════════════════════════════════════
# JC4: 临时构建产物
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC4: 临时构建产物检测..."

JC4_HITS=""
HITS=$(echo "$CHECK_FILES" | grep -E '/staging/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '/build/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '__pycache__/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.pyc$' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E '\.patch-backup' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"
HITS=$(echo "$CHECK_FILES" | grep -E 'EXCLUDE_LIST$|TASK_CARD\.md$' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

if [ -n "$(echo "$JC4_HITS" | tr -d '[:space:]')" ]; then
    JC4_COUNT=$(echo -e "$JC4_HITS" | grep -c . || true)
    fail "JC4: ${JC4_COUNT} 个临时构建产物被跟踪:"
    echo -e "$JC4_HITS" | head -10 | sed 's/^/       /'
fi

# ═══════════════════════════════════════════════════════════════
# 汇总
# ═══════════════════════════════════════════════════════════════
echo ""
if [ "$ERRORS" -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} 未发现杂项文件"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Junk Files: ${ERRORS}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "JC_RESULT=$([ $ERRORS -eq 0 ] && echo 'pass' || echo 'fail')"
echo "JC_ERRORS=${ERRORS}"

if [ "$ERRORS" -eq 0 ]; then
    exit 0
else
    exit 1
fi
