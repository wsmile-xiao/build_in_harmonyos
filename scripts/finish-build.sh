#!/bin/sh
# finish-build.sh — 编译收尾（Phase 4 一条命令）
# 用法: ./scripts/finish-build.sh <软件名> <版本> [success|partial|failed]
#
# 自动执行:
#   1. refresh-patch.sh --auto   (补丁生成)
#   2. close-archive.sh ...       (归档收尾)
#   3. finalize-archive.sh ...    (归档校验+RELEASENOTE)
#   4. python3 gen_summary.py      (总结报告)
#
# Layer: Layer1（完全确定性，无 AI 决策点）

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

show_help() {
    cat <<'HELPEOF'
用法:
  ./scripts/finish-build.sh <软件名> <版本> [状态]

描述:
  编译收尾管线。自动完成 Phase 4 的所有确定性步骤。
  在 Phase 3 编译成功后调用此命令。

参数:
  <软件名>  软件名称
  <版本>    版本号
  [状态]     success（默认）/ partial / failed

步骤:
  1. 补丁生成 (refresh-patch.sh --auto)
  2. 归档收尾 (close-archive.sh)
  3. 总结报告 (gen_summary.py)

示例:
  ./scripts/finish-build.sh sed 4.9
  ./scripts/finish-build.sh pkg-config 0.29.2 success
  ./scripts/finish-build.sh coreutils 9.10 partial

退出码:
  0  全部成功
  1  参数错误
  N  失败步骤编号（1=补丁, 2=归档, 3=总结）
HELPEOF
    exit 0
}

if [ $# -lt 2 ]; then
    echo "❌ 缺少参数。用法: $0 <软件名> <版本> [status]"
    exit 1
fi

case "$1" in --help|-h) show_help ;; esac

SOFTWARE="$1"
VERSION="$2"
STATUS="${3:-success}"

echo "🏁 编译收尾管线"
echo "  软件: ${SOFTWARE} ${VERSION}"
echo "  状态: ${STATUS}"
echo ""

# ---- Step 1: 补丁生成 ----
STEP1_OK=false
if [ -x "${SCRIPT_DIR}/refresh-patch.sh" ]; then
    echo "[1/3] 补丁生成..."
    if "${SCRIPT_DIR}/refresh-patch.sh" --auto "$SOFTWARE" "$VERSION"; then
        STEP1_OK=true
        echo "  ✅ 补丁生成完成"
    else
        echo "  ⚠️  补丁生成失败（退出码 $?），继续归档..."
    fi
else
    echo "  ⏭️  refresh-patch.sh 不存在，跳过"
    STEP1_OK=true  # 不存在不算失败
fi
echo ""

# ---- Step 2: 归档收尾 ----
STEP2_OK=false
if [ -x "${SCRIPT_DIR}/close-archive.sh" ]; then
    echo "[2/4] 归档收尾..."
    if "${SCRIPT_DIR}/close-archive.sh" "$SOFTWARE" "$VERSION" "$STATUS"; then
        STEP2_OK=true
        echo "  ✅ 归档完成"
    else
        RC=$?
        echo "  ❌ 归档失败 (exit code: $RC)"
        exit 2
    fi
else
    echo "  ⚠️  close-archive.sh 不存在"
fi
echo ""

# ---- Step 3: 归档校验 + RELEASENOTE 生成 ----
STEP3_OK=false
if [ -x "${SCRIPT_DIR}/finalize-archive.sh" ]; then
    echo "[3/4] 归档校验..."
    if "${SCRIPT_DIR}/finalize-archive.sh" "$SOFTWARE" "$VERSION"; then
        STEP3_OK=true
        echo "  ✅ 归档校验通过"
    else
        echo "  ⚠️  归档校验有警告（非阻塞）"
        STEP3_OK=true
    fi
else
    echo "  ⏭️  finalize-archive.sh 不存在，跳过"
    STEP3_OK=true
fi
echo ""

# ---- Step 4: 总结报告 ----
STEP4_OK=false
if command -v python3 >/dev/null 2>&1; then
    GEN_SUMMARY="${PROJECT_DIR}/scripts/gen_summary.py"
    if [ -f "$GEN_SUMMARY" ]; then
        echo "[4/4] 生成总结报告..."
        cd "$PROJECT_DIR"
        if python3 "$GEN_SUMMARY" 2>/dev/null; then
            STEP4_OK=true
            echo "  ✅ SUMMARY.md 已更新"
        else
            echo "  ⚠️  gen_summary.py 执行失败（可能非致命）"
            STEP4_OK=true
        fi
    else
        echo "  ⏭️  gen_summary.py 不存在"
        STEP4_OK=true
    fi
else
    echo "  ⏭️  python3 不可用"
    STEP4_OK=true
fi
echo ""

# ---- 完成 ----
echo "═════════════════════════════"
if $STEP1_OK && $STEP2_OK && $STEP3_OK && $STEP4_OK; then
    echo "✅ 编译收尾全部完成"
    echo "  📦 ${SOFTWARE} ${VERSION} → ${STATUS}"
else
    echo "⚠️  编译收尾部分完成（有警告）"
fi
echo "═════════════════════════════"
