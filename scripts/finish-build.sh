#!/bin/sh
# ==============================================================================
# [Layer 2] finish-build.sh - 编译收尾管线（Phase 4 一条命令）
# ==============================================================================
# 层级: L2(半自动)
# 决策点: 极少(状态判断分支和步骤容错)
# 入口: ./scripts/finish-build.sh <软件名> <版本> [success|partial|failed]
# 依赖: refresh-patch.sh, close-archive.sh, verify-build.sh, finalize-archive.sh, gen_summary.py
# 调用者: AI / 用户（Phase 3 编译成功后调用）
# ==============================================================================
# 用法: ./scripts/finish-build.sh <软件名> <版本> [success|partial|failed]
#
# 自动执行:
#   1. refresh-patch.sh --auto   (补丁生成)
#   2. close-archive.sh ...       (归档收尾)
#   3. verify-build.sh ...        (质量门禁 G1-G4)
#   4. finalize-archive.sh ...    (归档校验+RELEASENOTE)
#   5. python3 gen_summary.py      (总结报告)

# ⚠️ 不使用 set -e：每个步骤独立判断成败，一步失败不阻塞后续步骤
#    （旧版用 set-e 导致 close-archive 失败时 finalize-archive 永远不被调用）

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
  3. 质量门禁 (verify-build.sh)          ← 新增
  4. 归档校验 (finalize-archive.sh)
  5. 总结报告 (gen_summary.py)

示例:
  ./scripts/finish-build.sh sed 4.9
  ./scripts/finish-build.sh pkg-config 0.29.2 success
  ./scripts/finish-build.sh coreutils 9.10 partial

退出码:
  0  全部成功
  1  参数错误
  N  失败步骤编号（1=补丁, 2=归档, 3=验证, 4=校验, 5=总结）
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
TIMESTAMP="$(date '+%Y%m%d%H%M%S')"

echo "🏁 编译收尾管线"
echo "  软件: ${SOFTWARE} ${VERSION}"
echo "  状态: ${STATUS}"
echo ""

# 计算归档目录（必须在关卡检查之前）
FIRST_LETTER="$(echo "$SOFTWARE" | cut -c1 | tr 'A-Z' 'a-z')"
ARCHIVE_DIR="${PROJECT_DIR}/archives/${FIRST_LETTER}/${SOFTWARE}/${VERSION}"

# ---- 任务卡（与 build-driver 共享）----
TASK_CARD="${ARCHIVE_DIR}/TASK_CARD.md"
if [ -f "${SCRIPT_DIR}/_task_card.sh" ]; then
    . "${SCRIPT_DIR}/_task_card.sh"
fi

# ════════════════════════════════════════
#   Step 0: 前置关卡闸门（流程完整性检查）
# ════════════════════════════════════════
#   检查 AI 是否跳过了必要步骤，缺失则 warn + 记录 + 可能降级状态
echo "[0/6] 流程完整性关卡..."

_GATE_MISS=0
_GATE_WARNINGS=""

# --- 关卡 A: test-report.md（make check / make test 结果）---
if [ ! -f "${ARCHIVE_DIR}/reports/test-report.md" ]; then
    echo "  ⚠️  [关卡A] 缺少 test-report.md"
    echo "      → 请在 finish-build 前执行: make check 或 make test"
    echo "      → 将结果写入: reports/test-report.md"
    _GATE_MISS=$((_GATE_MISS + 1))
    _GATE_WARNINGS="${_GATE_WARNINGS} test-report:missing"
    # success → partial（测试是质量保证的核心步骤）
    if [ "$STATUS" = "success" ]; then
        STATUS="partial"
        echo "      → 状态降级: success → partial"
    fi
else
    echo "  ✅ [关卡A] test-report.md 存在"
fi

# --- 关卡 B: Staging 目录验证标记（原 Phase 2.5）---
_25_MARK="${ARCHIVE_DIR}/.staging-verified"
if [ ! -f "$_25_MARK" ]; then
    echo "  ⚠️  [关卡B] 缺少 Staging 验证标记 (${_25_MARK})"
    echo "      → 请执行 SKILL.md §2.8 Staging 目录验证"
    _GATE_MISS=$((_GATE_MISS + 1))
    _GATE_WARNINGS="${_GATE_WARNINGS} staging:missing"
else
    echo "  ✅ [关卡B] Phase 2.5 已通过 ($(cat "$_25_MARK" 2>/dev/null | head -1))"
fi

# --- 关卡 C: 预编译包交付物 ---
if [ ! -d "${ARCHIVE_DIR}/packaging" ] || \
   [ -z "$(ls "${ARCHIVE_DIR}/packaging/"*ohos-aarch64*.tar.gz 2>/dev/null)" ]; then
    echo "  ⚠️  [关卡C] 缺少预编译包交付物 (packaging/*-ohos-aarch64.tar.gz)"
    echo "      → 请执行 SKILL.md §Step 5 打包流程 (package.sh)"
    _GATE_MISS=$((_GATE_MISS + 1))
    _GATE_WARNINGS="${_GATE_WARNINGS} packaging:missing"
else
    _PKG_COUNT=$(ls "${ARCHIVE_DIR}/packaging/"*ohos-aarch64*.tar.gz 2>/dev/null | wc -l | tr -d ' ')
    echo "  ✅ [关卡C] 预编译包存在 (${_PKG_COUNT} 个 tar.gz)"
fi

# --- 关卡汇总 ---
if [ "$_GATE_MISS" -gt 0 ]; then
    echo ""
    echo "  🚨 关卡结果: ${_GATE_MISS} 个必要步骤被跳过"
    echo "     缺失项:${_GATE_WARNINGS}"
    echo "     建议: 按 SKILL.md 五步走完整执行后再运行 finish-build.sh"
    # 写入 manifest 以便追踪
    if [ -f "${ARCHIVE_DIR}/manifest.yaml" ]; then
        sed -i '/^skipped_gates:/d' "${ARCHIVE_DIR}/manifest.yaml"
        echo "skipped_gates: ${_GATE_WARNINGS}" >> "${ARCHIVE_DIR}/manifest.yaml"
    fi
else
    echo ""
    echo "  ✅ 全部关卡通过"
fi
echo ""

# ---- Step 1: 补丁生成 ----
STEP1_OK=false
if [ -x "${SCRIPT_DIR}/refresh-patch.sh" ]; then
    echo "[1/5] 补丁生成..."
    if "${SCRIPT_DIR}/refresh-patch.sh" --auto "$SOFTWARE" "$VERSION"; then
        STEP1_OK=true
        echo "  ✅ 补丁生成完成"
        update_task_card 11a "✅完成" "refresh-patch OK"
    else
        echo "  ⚠️  补丁生成失败（退出码 $?），继续归档..."
        update_task_card 11a "⚠️部分" "refresh-patch 失败"
    fi
else
    echo "  ⏭️  refresh-patch.sh 不存在，跳过"
    STEP1_OK=true  # 不存在不算失败
    update_task_card 11a "⏭️跳过" "脚本不存在"
fi
echo ""

# ---- Step 2: 归档收尾 ----
STEP2_OK=false
if [ -x "${SCRIPT_DIR}/close-archive.sh" ]; then
    echo "[2/5] 归档收尾..."
    if _SKIP_PATCH_GENERATION=true "${SCRIPT_DIR}/close-archive.sh" "$SOFTWARE" "$VERSION" "$STATUS"; then
        STEP2_OK=true
        echo "  ✅ 归档完成"
        update_task_card 11b "✅完成" "close-archive OK"
    else
        RC=$?
        echo "  ❌ 归档失败 (exit code: $RC)，继续后续步骤..."
        update_task_card 11b "❌失败" "exit $RC"
        # 不再 exit 2！允许 finalize-archive 等后续步骤继续执行
    fi
else
    echo "  ⚠️  close-archive.sh 不存在"
    update_task_card 11b "⏭️跳过" "脚本不存在"
fi
echo ""

# ---- Step 3: 质量门禁验证 (G1-G4) ----
STEP3_OK=false
echo "[3/5] 运行质量门禁验证 (verify-build.sh)..."

# 计算归档目录（与 close-archive.sh 相同逻辑）— 已在 Step 0 前计算
VERIFY_LOG="${ARCHIVE_DIR}/logs/verify-${TIMESTAMP:-$(date '+%Y%m%d%H%M%S')}.log"

if [ -f "${PROJECT_DIR}/scripts/verify-build.sh" ]; then
    # 加载 .build-context 以获取 DEFAULT_PREFIX
    if [ -f "${ARCHIVE_DIR}/.build-context" ]; then
        . "${ARCHIVE_DIR}/.build-context"
    fi

    sh "${PROJECT_DIR}/scripts/verify-build.sh" \
        --software "$SOFTWARE" \
        --version "$VERSION" \
        --archive-dir "$ARCHIVE_DIR" \
        --install-prefix "${TEST_PREFIX:-$DEFAULT_PREFIX}" \
        2>&1 | tee "$VERIFY_LOG"
    VERIFY_RC=${PIPESTATUS[0]:-$?}

    if [ "$VERIFY_RC" -eq 0 ]; then
        echo "  ✅ 质量门禁全部通过"
        STEP3_OK=true
        update_task_card 11c "✅完成" "G1-G4 全通过"
        # 保持或升级状态：验证通过不降低已有状态
        case "$STATUS" in
            failed) STATUS="partial" ;;   # 验证通过至少是 partial
            *) ;;                          # success/partial 保持不变
        esac
    else
        echo "  ⚠️  质量门禁有警告/失败 (RC=$VERIFY_RC)，继续归档但标记状态"
        STEP3_OK=true  # 非阻塞，继续后续步骤
        update_task_card 11c "⚠️部分" "G1-G4 RC=$VERIFY_RC"
        # 验证失败则降级状态
        case "$STATUS" in
            success) STATUS="partial" ;;
            partial) STATUS="failed" ;;
            *) ;;  # failed 保持不变
        esac
    fi
else
    echo "  ⏭️  verify-build.sh 不存在，跳过验证"
    STEP3_OK=true  # 不存在不算失败
    update_task_card 11c "⏭️跳过" "脚本不存在"
fi
echo ""

# ---- Step 4: 归档校验 + RELEASENOTE 生成 ----
STEP4_OK=false
if [ -x "${SCRIPT_DIR}/finalize-archive.sh" ]; then
    echo "[4/5] 归档校验..."
    if "${SCRIPT_DIR}/finalize-archive.sh" "$SOFTWARE" "$VERSION"; then
        STEP4_OK=true
        echo "  ✅ 归档校验通过"
        update_task_card 11d "✅完成" "finalize OK"
    else
        echo "  ⚠️  归档校验有警告（非阻塞）"
        STEP4_OK=true
        update_task_card 11d "⚠️部分" "有警告"
    fi
else
    echo "  ⏭️  finalize-archive.sh 不存在，跳过"
    STEP4_OK=true
    update_task_card 11d "⏭️跳过" "脚本不存在"
fi
echo ""

# ---- Step 5: 总结报告 ----
STEP5_OK=false
if command -v python3 >/dev/null 2>&1; then
    GEN_SUMMARY="${PROJECT_DIR}/scripts/gen_summary.py"
    if [ -f "$GEN_SUMMARY" ]; then
        echo "[5/5] 生成总结报告..."
        cd "$PROJECT_DIR"
        if python3 "$GEN_SUMMARY" 2>/dev/null; then
            STEP5_OK=true
            echo "  ✅ SUMMARY.md 已更新"
            update_task_card 11e "✅完成" "gen_summary OK"
        else
            echo "  ⚠️  gen_summary.py 执行失败（可能非致命）"
            STEP5_OK=true
            update_task_card 11e "⚠️部分" "执行失败"
        fi
    else
        echo "  ⏭️  gen_summary.py 不存在"
        STEP5_OK=true
        update_task_card 11e "⏭️跳过" "脚本不存在"
    fi
else
    echo "  ⏭️  python3 不可用"
    STEP5_OK=true
    update_task_card 11e "⏭️跳过" "python3不可用"
fi
echo ""

# ---- 完成 ----
echo "═════════════════════════════"
if $STEP1_OK && $STEP2_OK && $STEP3_OK && $STEP4_OK && $STEP5_OK; then
    echo "✅ 编译收尾全部完成"
    echo "  📦 ${SOFTWARE} ${VERSION} → ${STATUS}"
else
    echo "⚠️  编译收尾部分完成（有警告）"
fi
echo "═════════════════════════════"
