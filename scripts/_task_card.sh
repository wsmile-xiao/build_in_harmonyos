#!/bin/sh
# ==============================================================================
# _task_card.sh — 任务卡共享函数（被 build-driver.sh / finish-build.sh source）
# ==============================================================================

# TASK_CARD 路径（由调用者在 source 前设置）
# 默认值：如果未设置则从第一个参数或环境变量推导
: "${TASK_CARD:=}"

# 初始化任务卡
init_task_card() {
    _tc_software="${1:-UNKNOWN}"
    _tc_version="${2:-unknown}"
    _tc_dir="$(dirname "$TASK_CARD")"
    mkdir -p "$_tc_dir" 2>/dev/null
    
    cat > "$TASK_CARD" << TCEOF
# 任务卡 — ${_tc_software} ${_tc_version}
# 创建: $(date)
# 状态: 进行中

## 主步骤 (1-13)

| # | 步骤 | 状态 | 时间 | 备注 |
|---|------|------|------|------|
| 1 | init-build (初始化) | ⬜ 待执行 | — | |
| 2 | apply-patches (补丁) | ⬜ 待执行 | — | |
| 3 | configure (配置) | ⬜ 待执行 | — | |
| 4 | make (编译) | ⬜ 待执行 | — | |
| 5 | install (安装) | ⬜ 待执行 | — | |
| 6 | 安全弹窗 R7 | ⬜ 待执行 | — | |
| 7 | make check (测试) | ⬜ 待执行 | — | |
| 8 | Staging 验证 | ⬜ 待执行 | — | |
| 9 | package (打包) | ⬜ 待执行 | — | |
| 10 | deploy (部署) | ⬜ 待执行 | — | |
| 11a | refresh-patch (补丁生成) | ⬜ 待执行 | — | finish-build 子步骤 |
| 11b | close-archive (归档收尾) | ⬜ 待执行 | — | finish-build 子步骤 |
| 11c | verify-build (质量门禁 G1-G4) | ⬜ 待执行 | — | finish-build 子步骤 |
| 11d | finalize-archive (归档校验) | ⬜ 待执行 | — | finish-build 子步骤 |
| 11e | gen_summary (总结报告) | ⬜ 待执行 | — | finish-build 子步骤 |
| 12 | 归档校准 | ⬜ 待执行 | — | |
| 13 | 清理 | ⬜ 待执行 | — | |

---
*最后更新: $(date)*
TCEOF
}

# 更新任务卡某一步状态
# 用法: update_task_card <步骤号> <状态> [备注]
update_task_card() {
    [ -z "$TASK_CARD" ] && return
    [ ! -f "$TASK_CARD" ] && return
    
    _step_num="$1"
    _step_status="$2"
    _step_note="${3:-}"
    _now_time="$(date '+%H:%M')"
    
    # 用 sed 精确替换该行的状态列
    sed -i "/^| ${_step_num} |/{
        s/| ⬜ 待执行 |/| ${_step_status} |/
        s/| 🔧 手动模式 |/| ${_step_status} |/
        s/| ⏭️ 跳过 |/| ${_step_status} |/
        s/| — |/| ${_now_time} |/
    }" "$TASK_CARD" 2>/dev/null
    
    # 如果有备注且该行为空备注，填入
    if [ -n "$_step_note" ]; then
        sed -i "/^| ${_step_num} |/{
            s/| $/| ${_step_note} |/
            s/| finish-build 子步骤 |/| ${_step_note} |/
        }" "$TASK_CARD" 2>/dev/null
    fi
}

# 检查任务卡完成度并输出报告
check_task_card() {
    [ -z "$TASK_CARD" ] && { echo "⚠️ TASK_CARD 未设置"; return; }
    [ ! -f "$TASK_CARD" ] && { echo "⚠️ 任务卡不存在: $TASK_CARD"; return; }
    
    _total=13
    _done=$(grep -c '✅完成' "$TASK_CARD" 2>/dev/null || echo 0)
    _pending=$(grep -c '⬜ 待执行' "$TASK_CARD" 2>/dev/null || echo 0)
    _manual=$(grep -c '🔧手动' "$TASK_CARD" 2>/dev/null || echo 0)
    _partial=$(grep -c '⚠️部分' "$TASK_CARD" 2>/dev/null || echo 0)
    _failed=$(grep -c '❌失败' "$TASK_CARD" 2>/dev/null || echo 0)
    
    echo ""
    echo "╔══════════════════════════════════════════════════════════╗"
    echo "║  📋 任务卡检查 — ${_done}/${_total} 主步骤完成                  ║"
    echo "╠══════════════════════════════════════════════════════════╣"
    
    # 主步骤状态
    if [ "$_pending" -gt 0 ]; then
        echo "║  ⬜️  $_pending 个待执行:                                    ║"
        grep '⬜ 待执行' "$TASK_CARD" | grep -v '11[abcde]' | while IFS='|' read _n _s _st _t _note; do
            [ -z "$_s" ] || [ "$_s" = " " ] || echo "║      → $(echo "$_s" | tr -d ' ')                              ║"
        done
    fi
    if [ "$_failed" -gt 0 ]; then
        echo "║  ❌  $_failed 个失败                                         ║"
        grep '❌失败' "$TASK_CARD" | while IFS='|' read _n _s _st _t _note; do
            [ -z "$_s" ] || echo "║      → $(echo "$_s" | tr -d ' ')                              ║"
        done
    fi
    
    # 质量子步骤专项检查（11a-11e）
    echo "║                                                      ║"
    echo "║  【质量关卡子步骤】                                     ║"
    for _sub in 11a 11b 11c 11d 11e; do
        _sub_line=$(grep "^| ${_sub} |" "$TASK_CARD" 2>/dev/null)
        _sub_status=$(echo "$_sub_line" | sed 's/.*| *\([^|]*\) *|.*/\1/')
        _sub_name=$(echo "$_sub_line" | sed 's/.*| *\([^|]*\) *.*/\1/')
        case "$_sub_status" in
            *✅*)   echo "║      ✅ $_sub_name" ;;
            *⚠️*|*❌*) echo "║      ❌ $_sub_name ← 需关注!" ;;
            *)       echo "║      ⬜ $_sub_name" ;;
        esac
    done
    
    echo "╠══════════════════════════════════════════════════════════╣"
    if [ "$((_done + _manual))" -ge "$_total" ] && [ "$_failed" -eq 0 ]; then
        echo "║  ✅ 全部主步骤已完成                                      ║"
    else
        echo "║  💡 存在未完成步骤，请继续                                 ║"
    fi
    echo "╚══════════════════════════════════════════════════════════╝"
}
