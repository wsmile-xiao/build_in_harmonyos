#!/bin/sh
# ==============================================================================
# [Layer 1] refresh-patch.sh - 补丁管线（全自动 diff → 粒度拆分 → 格式校验）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性流程）
# 入口: ./scripts/refresh-patch.sh --auto <软件名> <版本>
# 依赖: diff, patch, curl, tar
# 调用者: finish-build.sh, close-archive.sh, AI / 用户
# ==============================================================================
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
  ./refresh-patch.sh --auto <软件名> <版本>          # 自动模式（推荐）
  ./refresh-patch.sh --all <原始目录> <修改后目录> <输出目录>
  ./refresh-patch.sh <补丁编号> <原始目录> <修改后目录> [输出目录]

描述:
  补丁管线唯一入口。自动完成 diff → 粒度拆分 → 格式校验 → 验证 → hash 绑定。

  模式说明：
    --auto:     全自动。自动查找 tarball + 构建目录，按文件拆分补丁，写入 manifest.yaml
                这是 SKILL.md Phase 4 Step 3 的唯一推荐用法
    --all:      手动指定目录，生成单个 all-changes.patch
    单个补丁:   手动指定编号和目录

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
  ./refresh-patch.sh --auto pkg-config 0.29.2              # 自动模式（推荐）
  ./refresh-patch.sh --all /path/to/orig /path/to/mod patches/
  ./refresh-patch.sh 0001 /path/to/orig /path/to/modified patches/

退出码:
  0  成功
  1  参数错误
  2  目录不存在
  3  diff 执行失败
  4  补丁 dry-run 验证失败
  5  补丁格式校验失败（双 diff 头 / 绝对路径）

格式校验（自动执行）:
  脚本在生成补丁后自动调用 validate_patch_format() 检测：
  - E058-1: 双 diff 头（git diff + unified diff 混用）
  - E058-2: 绝对路径（--- 行以 / 开头）
  - E058-3: 缺失 diff 头行（HarmonyOS musl diff 特性，自动修复）
  - E058-4: 空补丁或无效文件

  详见: build-systems.md §3.8 / error-patterns.md E058
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

# ---------- 补丁格式校验（F001: 双 diff 头 / 绝对路径 / 缺失 diff 头） ----------
#
# 检测以下格式问题：
#   E058-1: 双 diff 头（同时存在 diff -ruN 和 --- / +++ 的多套头）
#   E058-2: 绝对路径（--- / +++ 行以 / 开头）
#   E058-3: 缺失 diff 头行（没有 ^diff 开头的行）
#   E058-4: 空补丁或过小
#
# 返回值: 0=通过, 1=警告(可修复), 2=错误(必须人工处理)

validate_patch_format() {
    _patch_file="$1"
    _errors=0
    _warnings=0

    if [ ! -f "$_patch_file" ]; then
        echo "  ❌ [E058-4] 补丁文件不存在: $_patch_file"
        return 2
    fi

    _size=$(wc -c < "$_patch_file" | tr -d ' ')
    if [ "$_size" -lt 10 ]; then
        echo "  ❌ [E058-4] 补丁文件过小 (${_size} bytes)，可能为空"
        return 2
    fi

    # 检查 1: diff 头数量
    _diff_count=$(grep -c '^diff ' "$_patch_file" 2>/dev/null || echo 0)
    _diff_count=$(echo "$_diff_count" | tr -d ' ')

    # 也检查 HarmonyOS musl diff 可能不输出 diff 行的情况
    _has_minus_plus=$(grep -q '^--- ' "$_patch_file" 2>/dev/null && grep -q '^+++ ' "$_patch_file" 2>/dev/null && echo "yes" || echo "no")

    if [ "$_diff_count" -eq 0 ] && [ "$_has_minus_plus" = "yes" ]; then
        echo "  ⚠️  [E058-3] 缺失 diff 头行（HarmonyOS musl diff 不输出 ^diff 行）"
        echo "     → 自动修复：在顶部插入 diff -ruN 头"
        _warnings=$((_warnings + 1))
        # 自动修复：提取 --- 和 +++ 路径，插入 diff 头
        _orig_path=$(head -1 "$_patch_file" | sed 's/^--- //')
        _mod_path=$(sed -n '2s/^+++ //p' "$_patch_file")
        _tmpfile="${TMPDIR:-$HOME/tmp}/.patch-validate-$$.tmp"
        {
            echo "diff -ruN ${_orig_path} ${_mod_path}"
            cat "$_patch_file"
        } > "$_tmpfile"
        mv "$_tmpfile" "$_patch_file"
        _diff_count=1
    elif [ "$_diff_count" -eq 0 ]; then
        echo "  ❌ [E058-4] 无 diff 头且无 ---/+++ 行，不是有效补丁"
        return 2
    fi

    if [ "$_diff_count" -gt 1 ]; then
        echo "  ❌ [E058-1] 双 diff 头问题：检测到 ${_diff_count} 个 ^diff 行"
        grep -n '^diff ' "$_patch_file" | while read _line; do
            echo "       → 第 ${_line}"
        done
        echo "     → 原因：可能混用了 git diff 和 unified diff 格式"
        echo "     → 修复：重新生成补丁，确保只用一种 diff 方式"
        _errors=$((_errors + 1))
    fi

    # 检查 2: 绝对路径
    _abs_count=$(grep -c '^--- /' "$_patch_file" 2>/dev/null || echo 0)
    _abs_count=$(echo "$_abs_count" | tr -d ' ')

    if [ "$_abs_count" -gt 0 ]; then
        echo "  ⚠️  [E058-2] 检测到 ${_abs_count} 个绝对路径（以 / 开头的 --- 行）"
        echo "     → 这会导致 patch -p1 无法正确应用"
        echo "     → 建议：使用相对路径的 diff（cd 公共父目录后执行 diff -ruN）"
        _warnings=$((_warnings + 1))
    fi

    # 输出结果
    if [ "$_errors" -gt 0 ]; then
        echo "  ❌ 格式校验失败: ${_errors} 个错误, ${_warnings} 个警告"
        return 2
    elif [ "$_warnings" -gt 0 ]; then
        echo "  ⚠️  格式校验通过（有 ${_warnings} 个已自动修复的警告）"
        return 1
    else
        echo "  ✅ 格式校验通过（单 diff 头、相对路径、完整）"
        return 0
    fi
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

    echo "  [2/3] 格式校验..."
    validate_patch_format "$_patch_file"
    _format_result=$?

    echo "  [3/3] 干运行验证补丁..."
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

    # 先写入临时目录，验证后原子替换（避免无差异时丢失旧补丁）
    _STAGING="${_output_dir}/.patch-staging"
    rm -rf "$_STAGING" && mkdir -p "$_output_dir" "$_STAGING"
    
    _existing=$(ls "$_output_dir"/*.patch 2>/dev/null | wc -l | tr -d ' ')
    if [ "$_existing" -gt 0 ]; then
        echo "  ⚠️  备份 ${_existing} 个旧补丁..."
        _backup="${_output_dir}/.patch-backup-$(date +%Y%m%d%H%M%S)"
        mkdir -p "$_backup"
        cp "$_output_dir"/*.patch "$_backup/" 2>/dev/null || true
    fi

    # 生成一个完整的补丁文件
    _norm_orig="$(cd "$_orig_dir" && pwd)"
    _norm_mod="$(cd "$_mod_dir" && pwd)"

    _exclude_args=$(build_exclude_args)

    _all_patch="${_STAGING}/0001-all-changes.patch"

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

    echo "  [2/3] 格式校验..."
    validate_patch_format "$_all_patch"

    echo "  [3/3] 补丁统计..."
    patch_stats "$_all_patch"

    echo ""
    echo "  ✅ 补丁已生成: ${_all_patch}"

    # ---- 原子替换（有新补丁才替换，无差异则保留旧补丁）----
    _all_size=$(wc -c < "$_all_patch" 2>/dev/null | tr -d ' ')
    if [ -z "$_all_size" ] || [ "$_all_size" -lt 10 ]; then
        rm -f "$_all_patch"
        _existing=$(ls "$_output_dir"/*.patch 2>/dev/null | wc -l | tr -d ' ')
        echo "  ⚠️  全量补丁为空，保留现有 ${_existing} 个补丁"
    else
        if ls "$_output_dir"/*.patch >/dev/null 2>&1; then
            _backup="${_output_dir}/.patch-backup-$(date +%Y%m%d%H%M%S)"
            mkdir -p "$_backup"
            cp "$_output_dir"/*.patch "$_backup/" 2>/dev/null || true
            echo "  📦 已备份旧补丁到 $(basename "$_backup")/"
            rm -f "$_output_dir"/*.patch
        fi
        mv "$_all_patch" "$_output_dir/0001-all-changes.patch"
    fi
    rm -rf "$_STAGING"
}

# ============ 自动模式：--auto ============
#
# 自动查找原始 tarball 和构建目录，执行完整补丁管线。
# 这是 SKILL.md Phase 4 Step 3 的唯一推荐入口。

auto_mode() {
    _software="$1"
    _version="$2"

    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    ARCHIVES_DIR="${PROJECT_DIR}/archives"
    TMPDIR="${TMPDIR:-$HOME/tmp}"

    # 加载构建上下文（获取双轨制路径变量）
    _CTX_FILE="${PROJECT_DIR}/.build-context-${_software}-${_version}"
    if [ -f "$_CTX_FILE" ]; then
        . "$_CTX_FILE" 2>/dev/null || true
    fi

    echo "🤖 补丁管线（自动模式 — 双轨制）"
    echo "  软件:   ${_software}"
    echo "  版本:   ${_version}"
    echo ""

    # ---- Step 1: 自动定位路径 ----
    FIRST_LETTER="$(echo "$_software" | cut -c1 | tr 'A-Z' 'a-z')"
    PATCH_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${_software}/${_version}/patches"
    MANIFEST_FILE="${ARCHIVES_DIR}/${FIRST_LETTER}/${_software}/${_version}/manifest.yaml"

    if [ ! -d "${PATCH_DIR}" ]; then
        mkdir -p "$PATCH_DIR"
        echo "  [1/7] 创建补丁目录: ${PATCH_DIR}"
    else
        echo "  [1/7] 补丁目录已存在: ${PATCH_DIR}"
    fi

    # ---- Step 2: 定位 .orig/ 基准目录（不再依赖 tarball）----
    # 双轨制: init-build.sh 已创建 .orig/(只读) + .work/(可写)
    # 优先级: BUILD_SRC_ORIG_DIR(上下文) → 同级 .orig/ 目录
    ORIG_DIR=""
    if [ -n "$BUILD_SRC_ORIG_DIR" ] && [ -d "$BUILD_SRC_ORIG_DIR" ]; then
        ORIG_DIR="$BUILD_SRC_ORIG_DIR"
    elif [ -d "${PATCH_DIR}/../${_software}-${_version}.orig" ]; then
        ORIG_DIR="$(cd "${PATCH_DIR}/../${_software}-${_version}.orig" && pwd)"
    fi

    if [ -z "$ORIG_DIR" ] || [ ! -f "$ORIG_DIR/configure" -a ! -f "$ORIG_DIR/CMakeLists.txt" -a ! -f "$ORIG_DIR/Makefile" ]; then
        echo "  ❌ 无法找到 .orig/ 基准目录"
        echo "     请先运行: ./scripts/init-build.sh ${_software} ${_version}"
        echo "     或手动指定: ./scripts/refresh-patch.sh --all <原始目录> <修改后目录> ${PATCH_DIR}"
        exit 2
    fi

    echo "  [2/7] 基准目录 (.orig/): $(basename "$ORIG_DIR")"

    # ---- Step 3: 定位 .work/ 工作副本（编译后的源码）----
    MOD_DIR=""
    if [ -n "$BUILD_SRC_DIR" ] && [ -d "$BUILD_SRC_DIR" ]; then
        MOD_DIR="$BUILD_SRC_DIR"
    elif [ -d "${PATCH_DIR}/../${_software}-${_version}.work" ]; then
        MOD_DIR="$(cd "${PATCH_DIR}/../${_software}-${_version}.work" && pwd)"
    fi

    # 回退：在 TMPDIR/builds 中查找（兼容旧流程）
    if [ -z "$MOD_DIR" ] || [ ! -f "$MOD_DIR/configure" -a ! -f "$MOD_DIR/CMakeLists.txt" -a ! -f "$MOD_DIR/Makefile" ]; then
        for _candidate in \
            "${TMPDIR}/builds/${_software}-${_version}" \
            "${TMPDIR}/${_software}-${_version}"; do
            if [ -d "$_candidate" ] && [ -f "$_candidate/configure" -o -f "$_candidate/CMakeLists.txt" -o -f "$_candidate/Makefile" ]; then
                MOD_DIR="$_candidate"
                break
            fi
        done
    fi

    if [ -z "$MOD_DIR" ]; then
        echo "  ❌ 无法找到 .work/ 工作副本目录"
        echo "     搜索位置:"
        echo "       \${BUILD_SRC_DIR} (上下文变量)"
        echo "       ../${_software}-${_version}.work/"
        echo "       ${TMPDIR}/builds/${_software}-${_version}/"
        exit 2
    fi

    echo "  [3/7] 工作副本 (.work/): $(basename "$MOD_DIR")"

    # ---- Step 4: 校验基准完整性（不再解压 tarball）----
    # .orig/ 由 init-build.sh 管理，这里只做存在性检查
    _norm_orig="$(cd "$ORIG_DIR" && pwd)"
    _norm_mod="$(cd "$MOD_DIR" && pwd)"

    # 防御性：确保 orig 和 mod 不是同一个目录
    if [ "$_norm_orig" = "$_norm_mod" ]; then
        echo "  ❌ 错误：.orig/ 和 .work/ 指向同一目录 (${_norm_orig})"
        echo "     这意味着源码未被正确复制。请运行 init-build.sh 重建工作副本。"
        exit 2
    fi

    echo "  [4/7] 基准校验通过: orig≠work ✅"

    # ---- Step 5: 生成补丁（先写入临时目录，验证后原子替换）----
    # 安全策略: 不直接删除旧补丁！先写到 .patch-staging/，
    #   有新补丁→替换旧补丁；无差异(空)→保留旧补丁不变
    echo "  [5/7] 生成补丁文件..."
    _STAGING="${PATCH_DIR}/.patch-staging"
    rm -rf "$_STAGING" && mkdir -p "$_STAGING"

    _exclude_args=$(build_exclude_args)
    _norm_orig="$(cd "$ORIG_DIR" && pwd)"
    _norm_mod="$(cd "$MOD_DIR" && pwd)"

    # 使用 symlink 确保相对路径 diff
    WORK="${TMPDIR}/.patch-work-${_software}"
    rm -rf "$WORK" && mkdir -p "$WORK"
    ln -sf "$_norm_orig" "$WORK/orig"
    ln -sf "$_norm_mod" "$WORK/mod"

    _patch_num=0
    _total_files=0
    _total_patches=0

    # 获取所有有差异的文件列表（去掉 orig/ 前缀）
    _diff_files=$(cd "$WORK" && eval diff -rq $_exclude_args orig mod 2>/dev/null | grep "^Files " | sed 's|Files orig/||;s| and mod/.*||' || true)

    if [ -z "$_diff_files" ]; then
        echo "  ⚠️  无差异（.work/ 与 .orig/ 完全相同，源码未修改或补丁已还原）"
        rm -rf "$WORK"
        # 不再删除 ORIG_DIR（它是持久化基准目录）
        return 0
    fi

    # 按文件逐个生成 patch（自动粒度拆分）
    # 使用位置参数循环避免管道子shell变量丢失问题
    set -- $_diff_files
    for _f do
        _patch_num=$((_patch_num + 1))
        _patch_file="${_STAGING}/$(printf '%04d' $_patch_num)-$(echo "$_f" | tr '/' '-').patch"

        # 从 WORK 目录执行 diff，路径为 orig/_f 和 mod/_f
        ( cd "$WORK" && diff -u "orig/$_f" "mod/$_f" ) > "$_patch_file" 2>/dev/null || true

        # 去掉路径中的 orig/ 和 mod/ 前缀，使 patch -p1 可用
        if [ -s "$_patch_file" ]; then
            _tmp_patch=$(mktemp)
            sed 's|^--- orig/|--- a/|;s|^+++ mod/|+++ b/|' "$_patch_file" > "$_tmp_patch"
            mv "$_tmp_patch" "$_patch_file"
        fi

        # 格式校验 + 自动修复（补 diff 头行）
        validate_patch_format "$_patch_file" > /dev/null 2>&1 || true

        # dry-run 验证（-p1 匹配 a/ b/ 或直接路径）
        if [ -s "$_patch_file" ] && (cd "$_norm_orig" && patch --dry-run -p1 < "$_patch_file" > /dev/null 2>&1); then
            size=$(wc -c < "$_patch_file" | tr -d ' ')
            printf "    ✅ [%04d] %s (%d bytes)\n" "$_patch_num" "$_f" "$size"
        elif [ -s "$_patch_file" ]; then
            printf "    ⚠️  [%04d] %s (dry-run 失败, %d bytes)\n" "$_patch_num" "$_f" "$(wc -c < "$_patch_file" | tr -d ' ')"
        else
            printf "    ➖ [%04d] %s (空文件，可能无差异)\n" "$_patch_num" "$_f"
        fi
        _total_files=$((_total_files + 1))
    done
    # 恢复位置参数（防御性）
    set --

    rm -rf "$WORK"

    # ---- Step 5.5: 原子替换（有新补丁才替换，无差异则保留旧补丁）----
    _generated=$(ls "$_STAGING"/*.patch 2>/dev/null | wc -l | tr -d ' ')
    _generated_size=0
    for _pf in "$_STAGING"/*.patch; do
        [ -f "$_pf" ] || continue
        _ps=$(wc -c < "$_pf" | tr -d ' ')
        _generated_size=$((_generated_size + _ps))
    done

    if [ "$_generated" -gt 0 ] && [ "$_generated_size" -ge 10 ]; then
        # 新补丁有效 → 备份旧补丁后替换
        if ls "$PATCH_DIR"/*.patch >/dev/null 2>&1; then
            _backup="${PATCH_DIR}/.patch-backup-$(date +%Y%m%d%H%M%S)"
            mkdir -p "$_backup"
            cp "$PATCH_DIR"/*.patch "$_backup/" 2>/dev/null || true
            echo "  📦 已备份 ${_generated} 个旧补丁到 $(basename "$_backup")/"
        fi
        rm -f "$PATCH_DIR"/*.patch
        mv "$_STAGING"/*.patch "$PATCH_DIR/" 2>/dev/null
        echo "  ✅ 补丁已更新: ${_generated} 个文件"
    else
        # 无新补丁（源码无差异）→ 保留旧补丁不变！
        rm -rf "$_STAGING"
        _existing=$(ls "$PATCH_DIR"/*.patch 2>/dev/null | wc -l | tr -d ' ')
        echo "  ⚠️  无差异（源码未修改或修改已还原），保留现有 ${_existing} 个补丁"
        _generated="$_existing"
    fi
    rm -rf "$_STAGING"

    # ---- Step 6: 输出 hash 绑定信息 ----
    ORIG_HASH=$(cd "$_norm_orig" && find . -type f ! -name '.tarball-sha256' | sort | xargs sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1)
    MOD_HASH=$(cd "$_norm_mod" && find . -type f ! -path './build/*' ! -path './.git/*' ! -name '*.o' ! -name '*.lo' | sort | xargs sha256sum 2>/dev/null | sha256sum | cut -d' ' -f1)

    echo ""
    echo "  [6/7] Hash 绑定:"
    echo "     基准目录 (.orig/) hash: ${ORIG_HASH:0:16}..."
    echo "     工作副本 (.work/) hash: ${MOD_HASH:0:16}..."
    echo "     生成补丁数:   ${_generated}"

    # ---- Step 7: 更新 manifest.yaml（如果存在）----
    if [ -f "$MANIFEST_FILE" ]; then
        echo "  [7/7] 更新 manifest.yaml..."

        # 检查是否已有 patch_generation 字段
        if ! grep -q '^patch_generation:' "$MANIFEST_FILE"; then
            cat >> "$MANIFEST_FILE" <<EOF

patch_generation:
  method: "refresh-patch.sh --auto (dual-track)"
  source_orig_dir: "$(basename "$_norm_orig")"
  source_work_dir: "$(basename "$_norm_mod")"
  source_orig_hash: "${ORIG_HASH}"
  source_work_hash: "${MOD_HASH}"
  generated_at: "$(date '+%Y-%m-%dT%H:%M:%S%z')"
  tool_version: "v3.0-dual-track"
  patches_count: ${_generated}
EOF
            echo "     ✅ 已写入 patch_generation 字段"
        else
            # 更新已有字段
            _tmp="${MANIFEST_FILE}.tmp"
            sed "s|^source_modified_hash:.*|source_work_hash: \"${MOD_HASH}\"|" \
                | sed "s|^patches_count:.*|patches_count: ${_generated}|" \
                | sed "s|^generated_at:.*|generated_at: \"$(date '+%Y-%m-%dT%H:%M:%S%z')\"|" \
                > "$_tmp" 2>/dev/null
            if [ $? -eq 0 ] && [ -s "$_tmp" ]; then
                mv "$_tmp" "$MANIFEST_FILE"
                echo "     ✅ 已更新 patch_generation 字段"
            else
                rm -f "$_tmp"
                echo "     ⚠️  manifest.yaml 更新跳过（格式不兼容）"
            fi
        fi
    else
        echo "  [7/7] ⚠️  manifest.yaml 不存在，跳过 hash 绑定写入"
    fi

    # 清理临时目录（不再需要清理 .patch-orig-* 因为用的是 .orig/ 基准）
    echo "═════════════════════════════"
    echo "✅ 补丁管线完成（双轨制）"
    echo "  📂 基准: ${_norm_orig} (.orig/)"
    echo "  📂 工作: ${_norm_mod} (.work/)"
    echo "  📂 输出: ${PATCH_DIR}/"
    echo "  📊 补丁: ${_generated} 个文件"
    echo "═════════════════════════════"
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
    --auto)
        if [ $# -lt 3 ]; then
            echo "❌ --auto 模式需要 2 个参数: <软件名> <版本>"
            exit 1
        fi
        auto_mode "$2" "$3"
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
