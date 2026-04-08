#!/bin/sh
# ==============================================================================
# [Layer 1] verify-symlinks.sh - 软链接可用性验证（全自动递归检查）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性检测）
# 入口: ./scripts/verify-symlinks.sh <目录>
# 依赖: readlink, ls, find
# 调用者: verify-build.sh, AI / 用户
# ==============================================================================
# verify-symlinks.sh - 验证目录下的软链接可用性
# 用法: ./verify-symlinks.sh <目录>
#
# 鸿蒙 HMDFS 的软链接行为异常，需要专门验证。
# 此脚本递归检查目录下所有软链接的可用性。

SCRIPT_NAME="$(basename "$0")"

show_help() {
    cat <<'HELPEOF'
用法:
  ./verify-symlinks.sh <目录>

描述:
  递归检查目录下所有软链接的可用性。
  针对鸿蒙 HMDFS 文件系统的特殊行为进行额外验证。

  对每个软链接执行以下检查：
  1. readlink 能否读取链接目标
  2. ls -la 检查链接是否存在（不依赖 test -e，因为 HMDFS 上可能不准确）
  3. 如果是 .so 文件，检查动态链接器能否找到

  输出报告使用以下标记：
  ✅  链接可用
  ❌  链接不可用
  ⚠️  疑似问题（如悬空链接、循环引用等）

参数:
  <目录>    要检查的目录路径

示例:
  ./verify-symlinks.sh /data/service/hnp/lib
  ./verify-symlinks.sh ./output/libs

退出码:
  0  所有链接正常
  >0  返回不可用链接的数量（上限 125）
HELPEOF
    exit 0
}

# ============ 主入口 ============
if [ $# -lt 1 ]; then
    echo "❌ 缺少参数。使用 --help 查看帮助。"
    exit 1
fi

case "$1" in
    --help|-h)
        show_help
        ;;
esac

TARGET_DIR="$1"

if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 目录不存在: $TARGET_DIR"
    exit 1
fi

echo "🔍 检查软链接: ${TARGET_DIR}"
echo "────────────────────────────"

# 由于管道的子 shell 问题，需要在管道外收集结果
# 使用临时文件
RESULT_FILE="${TMPDIR:-$HOME/tmp}/symlink_verify_$$.tmp"
broken_count=0
ok_count=0
warn_count=0
total_count=0

find "$TARGET_DIR" -type l 2>/dev/null | while read -r _symlink; do
    _target="$(readlink "$_symlink" 2>/dev/null)"

    _ls_info="$(ls -lad "$_symlink" 2>/dev/null)"
    _ls_exit=$?

    if [ -z "$_target" ] || [ "$_ls_exit" -ne 0 ] || echo "$_ls_info" | grep -q "No such file or directory"; then
        echo "BROKEN:${_symlink}" >> "$RESULT_FILE"
        continue
    fi

    # 检查目标
    _target_ok=false
    case "$_target" in
        /*)
            [ -e "$_target" ] && _target_ok=true
            ;;
        *)
            _link_dir="$(dirname "$_symlink")"
            _resolved_target="${_link_dir}/${_target}"
            if [ ! -e "$_resolved_target" ]; then
                echo "WARN:${_symlink}:${_target}" >> "$RESULT_FILE"
                continue
            fi
            _target_ok=true
            ;;
    esac

    if ! $_target_ok; then
        echo "BROKEN:${_symlink}" >> "$RESULT_FILE"
        continue
    fi

    # 循环链接检查
    _resolved="$(readlink -f "$_symlink" 2>/dev/null)"
    case "$_resolved" in
        "$_symlink"|"$_symlink/"*)
            echo "BROKEN:${_symlink}" >> "$RESULT_FILE"
            continue
            ;;
    esac

    # .so 文件额外检查
    case "$_symlink" in
        *.so|*.so.*)
            if [ -n "$_resolved" ] && [ -f "$_resolved" ]; then
                _magic="$(head -c 4 "$_resolved" 2>/dev/null)"
                if echo "$_magic" | grep -q 'ELF'; then
                    : # OK
                else
                    echo "WARN:${_symlink}:${_target}" >> "$RESULT_FILE"
                    continue
                fi
            fi
            ;;
    esac

    echo "OK:${_symlink}:${_target}" >> "$RESULT_FILE"
done

# 统计结果
if [ -f "$RESULT_FILE" ]; then
    broken_count=$(grep -c '^BROKEN:' "$RESULT_FILE" 2>/dev/null || echo 0)
    broken_count=$(echo "$broken_count" | tr -d ' ')
    ok_count=$(grep -c '^OK:' "$RESULT_FILE" 2>/dev/null || echo 0)
    ok_count=$(echo "$ok_count" | tr -d ' ')
    warn_count=$(grep -c '^WARN:' "$RESULT_FILE" 2>/dev/null || echo 0)
    warn_count=$(echo "$warn_count" | tr -d ' ')
    total_count=$(( ok_count + broken_count + warn_count ))

    # 详细输出
    echo ""
    echo "════════════════════════════"
    echo "📊 软链接验证报告"
    echo "════════════════════════════"

    # 输出 OK
    if [ "$ok_count" -gt 0 ]; then
        grep '^OK:' "$RESULT_FILE" | while IFS=: read -r _status _link _target; do
            echo "  ✅ [OK] ${_link} -> ${_target}"
        done
    fi

    # 输出 WARN
    if [ "$warn_count" -gt 0 ]; then
        grep '^WARN:' "$RESULT_FILE" | while IFS=: read -r _status _link _target; do
            echo "  ⚠️  [疑似问题] ${_link} -> ${_target}"
        done
    fi

    # 输出 BROKEN
    if [ "$broken_count" -gt 0 ]; then
        grep '^BROKEN:' "$RESULT_FILE" | while IFS=: read -r _status _link; do
            echo "  ❌ [不可用] ${_link}"
        done
    fi

    echo ""
    echo "────────────────────────────"
    echo "  总计:   ${total_count}"
    echo "  ✅ 可用: ${ok_count}"
    if [ "$warn_count" -gt 0 ]; then
        echo "  ⚠️  疑似: ${warn_count}"
    fi
    if [ "$broken_count" -gt 0 ]; then
        echo "  ❌ 不可用: ${broken_count}"
    fi
    echo "════════════════════════════"

    rm -f "$RESULT_FILE"

    # 返回不可用数量作为 exit code（上限 125）
    if [ "$broken_count" -gt 125 ]; then
        exit 125
    fi
    exit "$broken_count"
else
    echo ""
    echo "════════════════════════════"
    echo "📊 软链接验证报告"
    echo "════════════════════════════"
    echo "  总计:   0"
    echo "  ℹ️  未发现软链接"
    echo "════════════════════════════"
    exit 0
fi
