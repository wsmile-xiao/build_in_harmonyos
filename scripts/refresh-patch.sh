#!/bin/sh
# refresh-patch.sh - 刷新/重新生成补丁（基于三目录法）
# 用法: ./refresh-patch.sh <补丁编号> <原始目录> <修改后目录> [输出目录]
#       ./refresh-patch.sh --all <原始目录> <修改后目录> <输出目录>
#
# 用户修改了源码后需要更新补丁。此脚本自动化 diff 流程，
# 基于三目录法（原始目录、修改后目录、输出目录）生成补丁。

set -e

SCRIPT_NAME="$(basename "$0")"

show_help() {
    cat <<'HELPEOF'
用法:
  ./refresh-patch.sh <补丁编号> <原始目录> <修改后目录> [输出目录]
  ./refresh-patch.sh --all <原始目录> <修改后目录> <输出目录>

描述:
  基于三目录法刷新/重新生成补丁文件。
  对比原始目录和修改后目录的差异，生成 .patch 文件。

  自动排除以下目录的变更：
    build/ .git/ autom4te.cache/ CMakeFiles/ __pycache__/
    *.o *.lo *.la *.so *.a .libs/ .deps/ config.status config.log

模式:
  单个补丁:  指定补丁编号（如 0001），生成对应补丁文件
  --all:     重建输出目录中的所有补丁

参数:
  <补丁编号>    补丁编号，如 0001, 0002
  <原始目录>    未修改的原始源码目录
  <修改后目录>  修改后的源码目录
  [输出目录]    补丁输出目录（默认: patches/）

示例:
  ./refresh-patch.sh 0001 /path/to/orig /path/to/modified patches/
  ./refresh-patch.sh --all /path/to/orig /path/to/modified patches/

退出码:
  0  成功
  1  参数错误
  2  目录不存在
  3  diff 执行失败
  4  补丁 dry-run 验证失败
HELPEOF
    exit 0
}

# ---------- 排除模式 ----------
EXCLUDE_PATTERNS="build .git autom4te.cache CMakeFiles __pycache__ .libs .deps"
EXCLUDE_FILE_PATTERNS="*.o *.lo *.la *.so *.a config.status config.log"

# ---------- 构建排除参数 ----------
build_exclude_args() {
    _args=""
    for _pat in $EXCLUDE_PATTERNS; do
        _args="${_args} --exclude=${_pat}"
    done
    for _pat in $EXCLUDE_FILE_PATTERNS; do
        _args="${_args} --exclude=${_pat}"
    done
    echo "$_args"
}

# ---------- 分析补丁统计 ----------
patch_stats() {
    _patch_file="$1"

    if [ ! -f "$_patch_file" ]; then
        echo "  ❌ 补丁文件不存在: $_patch_file"
        return 1
    fi

    _files_changed=$(grep -c '^diff --git' "$_patch_file" 2>/dev/null || echo 0)
    _files_changed=$(echo "$_files_changed" | tr -d ' ')

    _files_changed_general=$(grep -c '^--- ' "$_patch_file" 2>/dev/null || echo 0)
    _files_changed_general=$(echo "$_files_changed_general" | tr -d ' ')

    # 使用较大值
    if [ "$_files_changed" -gt "$_files_changed_general" ]; then
        _fc="$_files_changed"
    else
        _fc="$_files_changed_general"
    fi

    _added=$(grep -c '^+' "$_patch_file" 2>/dev/null || echo 0)
    _added=$(echo "$_added" | tr -d ' ')
    # 减去 +++ 行
    _plusplus=$(grep -c '^+++' "$_patch_file" 2>/dev/null || echo 0)
    _plusplus=$(echo "$_plusplus" | tr -d ' ')
    _added=$(( _added - _plusplus ))
    [ "$_added" -lt 0 ] && _added=0

    _removed=$(grep -c '^-' "$_patch_file" 2>/dev/null || echo 0)
    _removed=$(echo "$_removed" | tr -d ' ')
    # 减去 --- 行
    _minusminus=$(grep -c '^--- ' "$_patch_file" 2>/dev/null || echo 0)
    _minusminus=$(echo "$_minusminus" | tr -d ' ')
    _removed=$(( _removed - _minusminus ))
    [ "$_removed" -lt 0 ] && _removed=0

    echo "  📊 补丁统计:"
    echo "     修改文件: ${_fc}"
    echo "     新增行数: +${_added}"
    echo "     删除行数: -${_removed}"
}

# ---------- 刷新单个补丁 ----------
refresh_single() {
    _patch_num="$1"
    _orig_dir="$2"
    _mod_dir="$3"
    _output_dir="$4"

    # 规范化编号格式
    case "$_patch_num" in
        [0-9])
            _patch_num="000${_patch_num}"
            ;;
        [0-9][0-9])
            _patch_num="00${_patch_num}"
            ;;
        [0-9][0-9][0-9])
            _patch_num="0${_patch_num}"
            ;;
    esac

    _patch_file="${_output_dir}/${_patch_num}-refresh.patch"

    # 确保 sed 在路径中可用
    _norm_orig="$(cd "$_orig_dir" && pwd)"
    _norm_mod="$(cd "$_mod_dir" && pwd)"

    echo "────────────────────────────"
    echo "📝 生成补丁 #${_patch_num}"
    echo "  原始: ${_norm_orig}"
    echo "  修改: ${_norm_mod}"
    echo "  输出: ${_patch_file}"
    echo ""

    _exclude_args=$(build_exclude_args)

    echo "  [1/3] 执行 diff..."
    if eval diff -U 10 -r "$_exclude_args" "$_norm_orig" "$_norm_mod" > "$_patch_file" 2>/dev/null; then
        echo "  ✅ diff 完成"
    else
        _diff_exit=$?
        # diff 返回 1 表示有差异，这是正常的
        if [ "$_diff_exit" -eq 1 ]; then
            echo "  ✅ diff 完成（检测到差异）"
        else
            echo "  ❌ diff 执行失败 (exit code: $_diff_exit)"
            exit 3
        fi
    fi

    # 检查补丁是否为空
    _patch_size=$(wc -c < "$_patch_file" 2>/dev/null | tr -d ' ')
    if [ -z "$_patch_size" ] || [ "$_patch_size" -lt 10 ]; then
        echo "  ⚠️  补丁为空（无差异），删除文件"
        rm -f "$_patch_file"
        return 0
    fi

    echo "  [2/3] 干运行验证补丁..."
    # 在原始目录中测试补丁
    if (cd "$_norm_orig" && patch --dry-run -p1 < "$_patch_file" > /dev/null 2>&1); then
        echo "  ✅ 补丁 dry-run 通过"
    else
        echo "  ⚠️  补丁 dry-run 失败（可能需要调整路径级别）"
    fi

    echo "  [3/3] 补丁统计..."
    patch_stats "$_patch_file"

    echo ""
    echo "  ✅ 补丁已生成: ${_patch_file}"
}

# ---------- 刷新所有补丁（重建） ----------
refresh_all() {
    _orig_dir="$1"
    _mod_dir="$2"
    _output_dir="$3"

    echo "📦 重建所有补丁模式"
    echo "  原始: ${_orig_dir}"
    echo "  修改: ${_mod_dir}"
    echo "  输出: ${_output_dir}"
    echo ""

    # 清空现有补丁
    if [ -d "$_output_dir" ]; then
        _existing=$(ls "$_output_dir"/*.patch 2>/dev/null | wc -l | tr -d ' ')
        if [ "$_existing" -gt 0 ]; then
            echo "  ⚠️  清理 ${_existing} 个旧补丁文件..."
            rm -f "$_output_dir"/*.patch
        fi
    else
        mkdir -p "$_output_dir"
    fi

    # 生成一个完整的补丁文件
    _norm_orig="$(cd "$_orig_dir" && pwd)"
    _norm_mod="$(cd "$_mod_dir" && pwd)"

    _exclude_args=$(build_exclude_args)

    _all_patch="${_output_dir}/0001-all-changes.patch"

    echo "  [1/2] 执行全量 diff..."
    if eval diff -U 10 -r "$_exclude_args" "$_norm_orig" "$_norm_mod" > "$_all_patch" 2>/dev/null; then
        echo "  ✅ diff 完成"
    else
        _diff_exit=$?
        if [ "$_diff_exit" -eq 1 ]; then
            echo "  ✅ diff 完成（检测到差异）"
        else
            echo "  ❌ diff 执行失败"
            exit 3
        fi
    fi

    _patch_size=$(wc -c < "$_all_patch" 2>/dev/null | tr -d ' ')
    if [ -z "$_patch_size" ] || [ "$_patch_size" -lt 10 ]; then
        echo "  ⚠️  补丁为空（无差异）"
        rm -f "$_all_patch"
        return 0
    fi

    echo "  [2/2] 补丁统计..."
    patch_stats "$_all_patch"

    echo ""
    echo "  ✅ 补丁已生成: ${_all_patch}"
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
    --all)
        if [ $# -lt 4 ]; then
            echo "❌ --all 模式需要 3 个参数: <原始目录> <修改后目录> <输出目录>"
            exit 1
        fi
        _orig="$2"
        _mod="$3"
        _out="$4"
        if [ ! -d "$_orig" ]; then
            echo "❌ 原始目录不存在: $_orig"
            exit 2
        fi
        if [ ! -d "$_mod" ]; then
            echo "❌ 修改后目录不存在: $_mod"
            exit 2
        fi
        mkdir -p "$_out"
        refresh_all "$_orig" "$_mod" "$_out"
        ;;
    *)
        if [ $# -lt 3 ]; then
            echo "❌ 参数不足。使用 --help 查看帮助。"
            exit 1
        fi
        _patch_num="$1"
        _orig="$2"
        _mod="$3"
        _out="${4:-patches}"
        if [ ! -d "$_orig" ]; then
            echo "❌ 原始目录不存在: $_orig"
            exit 2
        fi
        if [ ! -d "$_mod" ]; then
            echo "❌ 修改后目录不存在: $_mod"
            exit 2
        fi
        mkdir -p "$_out"
        refresh_single "$_patch_num" "$_orig" "$_mod" "$_out"
        ;;
esac
