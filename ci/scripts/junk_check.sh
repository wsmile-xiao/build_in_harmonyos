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

# ── 检查 git 跟踪的文件列表 ──
# 只检查 git tracked 文件（不是工作区所有文件）
TRACKED=$(git -C "${REPO_ROOT}" ls-files 2>/dev/null || true)

if [ -z "$TRACKED" ]; then
    echo "  非 git 仓库或无跟踪文件，跳过"
    echo "JC_RESULT=pass: no_git"; exit 0
fi

# ═══════════════════════════════════════════════════════════════
# JC1: 运行时状态文件
# ═══════════════════════════════════════════════════════════════
echo ""
echo "[step] JC1: 运行时状态文件检测..."

JC1_HITS=""
# .submit-state.json (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.submit-state\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

# .handoff.json (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.handoff\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

# .ci-result.json (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.ci-result\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

# .build-status.json
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.build-status\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

# ci-metadata.json (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/ci-metadata\.json$' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"

# .staging-* / .build-closed / .conan-verified 等
# 注意：排除 packaging/ 目录下的 .packaged（那是打包目录路径不是状态文件）
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.(staging-|build-closed|conan-verified|built|configured|installed|patched|tested|unpack|verify-passed)' || true)
JC1_HITS="${JC1_HITS}${HITS:+\n$HITS}"
# .packaged 状态文件（排除 packaging/ 目录下的同名路径）
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/\.packaged$' | grep -v '/packaging/\.packaged$' || true)
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

# *.a 静态库 (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*\.a$' || true)
JC2_HITS="${JC2_HITS}${HITS:+\n$HITS}"

# *.so 共享库 (archives 下，排除 conanfile 引用)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*\.so($|\.)' || true)
JC2_HITS="${JC2_HITS}${HITS:+\n$HITS}"

# *.o 目标文件
HITS=$(echo "$TRACKED" | grep -E '^archives/.*\.o$' || true)
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

# sources/ 目录
HITS=$(echo "$TRACKED" | grep -E '^sources/' || true)
JC3_HITS="${JC3_HITS}${HITS:+\n$HITS}"

# archives 下 *.tar.gz (排除 prebuilt.tar.gz)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*\.tar\.(gz|xz|bz2|tgz)$' | grep -v 'prebuilt' || true)
JC3_HITS="${JC3_HITS}${HITS:+\n$HITS}"

# archives 下 packaging/*.tar.gz
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/packaging/.*\.tar' || true)
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

# staging/ 目录
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/staging/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

# build/ 目录 (archives 下)
HITS=$(echo "$TRACKED" | grep -E '^archives/.*/build/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

# __pycache__
HITS=$(echo "$TRACKED" | grep -E '__pycache__/' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

# *.pyc
HITS=$(echo "$TRACKED" | grep -E '\.pyc$' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

# .patch-backup-*
HITS=$(echo "$TRACKED" | grep -E '\.patch-backup' || true)
JC4_HITS="${JC4_HITS}${HITS:+\n$HITS}"

# EXCLUDE_LIST / TASK_CARD.md
HITS=$(echo "$TRACKED" | grep -E 'EXCLUDE_LIST$|TASK_CARD\.md$' || true)
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

exit $([ $ERRORS -eq 0 ] && echo 0 || echo 1)
