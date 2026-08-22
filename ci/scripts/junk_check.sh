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
# 优先级 1: PR diff 模式（buildbot checkout-pr: shallow clone main + git apply pr.diff）
#   pr.diff 是 PR 文件清单的唯一权威来源：git apply 不产生 commit（diff 为空）、
#   新增文件不进 index（ls-files 看不见）、.build-closed 等被 .gitignore 忽略
#   （status --porcelain 也看不见），常规 git 命令三路全盲。
#   （2026-08-20 PR #3145 的 archives/p/pacvim/1.1.1/.build-closed 漏拦即此盲区）
# 优先级 2: incremental 模式：git diff origin/main...HEAD（本地开发分支）
# 优先级 3: full 模式：git ls-files（Release / 非 git 环境，无 origin/main 时回退）
JUNK_CHECK_MODE="incremental"

PR_DIFF="${JUNK_PR_DIFF:-${REPO_ROOT}/pr.diff}"
if [ -s "$PR_DIFF" ]; then
    # 提取 PR 涉及的新增/修改文件（重命名取新路径；纯删除 hunk 头是 +++ /dev/null，天然排除）
    CHECK_FILES=$(grep -E '^\+\+\+ b/' "$PR_DIFF" | sed -e 's|^+++ b/||' | grep -v '^/dev/null$' || true)
    if [ -n "$CHECK_FILES" ]; then
        JUNK_CHECK_MODE="prdiff"
    fi
fi

if [ "$JUNK_CHECK_MODE" != "prdiff" ]; then
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
# 备份/补丁残留（PR6091 教训: conandata.yml.ghfast-bak 混入提交）
HITS=$(echo "$CHECK_FILES" | grep -E '\.(bak|orig|rej|ghfast-bak)$' || true)
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
# JC5: archives 隐藏文件白名单（防 .build-closed 类运行时标记混入）
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC5: archives 隐藏文件白名单检测..."

# 白名单：git 常规 / lint 配置 / SKILL 工作流状态标记（含 main 存量全部形态）
# 新增工作流标记时须先在此登记，否则 CI 拦截（新增未登记 dotfile 一律 fail）
JC5_ALLOWED='/\.(gitignore|gitkeep|gitattributes|flake8|pylintrc|audit-result\.json|knowledge-done(-[a-z0-9._-]+)?|packaged|g0-verified(-cmake)?|g0-manual(ly)?-verif(y|ied)|no-patches-needed|patch-index|knowledge_gap_filled)$'

JC5_HITS=$(echo "$CHECK_FILES" | grep -E '^archives/.*/\.[^/]+$' | grep -Ev "$JC5_ALLOWED" || true)

if [ -n "$(echo "$JC5_HITS" | tr -d '[:space:]' )" ]; then
    JC5_COUNT=$(echo "$JC5_HITS" | grep -c . || true)
    fail "JC5: ${JC5_COUNT} 个 archives 下未登记的隐藏文件:"
    echo "$JC5_HITS" | grep . | head -10 | sed 's/^/       /'
    [ "$JC5_COUNT" -gt 10 ] && echo "       ... (共 ${JC5_COUNT} 个)"
    echo "       白名单: ci/scripts/junk_check.sh JC5_ALLOWED（新工作流标记请先登记再使用）"
fi

# ═══════════════════════════════════════════════════════════════
# JC6: PR 单软件原子性（W2：每个 PR 只允许提交一个软件）
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC6: PR 单软件原子性检测..."

if [ "$JUNK_CHECK_MODE" = "incremental" ] || [ "$JUNK_CHECK_MODE" = "prdiff" ]; then
    # 统计变更文件涉及的 archives/<首字母>/<软件名> 目录（同软件多版本算一个软件）
    JC6_PKGS=$(echo "$CHECK_FILES" | grep -E '^archives/[^/]+/[^/]+/' | cut -d'/' -f1-3 | sort -u || true)
    JC6_COUNT=$(echo "$JC6_PKGS" | grep -c . || true)
    if [ "$JC6_COUNT" -gt 1 ]; then
        fail "JC6: 本 PR 涉及 ${JC6_COUNT} 个软件包，违反 W2 单软件原子性（每个 PR 只允许一个软件）:"
        echo "$JC6_PKGS" | head -10 | sed 's/^/       /'
        [ "$JC6_COUNT" -gt 10 ] && echo "       ... (共 ${JC6_COUNT} 个)"
        echo "       修复: 每个软件单独开分支 feat/<软件名>-<版本>，只 add 对应目录后分别提 PR"
    else
        echo "  涉及软件数: ${JC6_COUNT}（合规）"
    fi
else
    echo "  full 模式（整仓扫描），跳过单软件检查"
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
