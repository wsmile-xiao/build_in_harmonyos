#!/bin/env zsh
setopt +o NOMATCH
# ==============================================================================
# [Layer 1] finalize-archive.sh - 归档收口校验（全自动清理+校验+整合）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性清理和校验流程）
# 入口: ./scripts/finalize-archive.sh <软件名> <版本>
# 依赖: manifest.yaml, PROGRESS.md, _meta.yaml
# 调用者: finish-build.sh, close-archive.sh, AI / 用户
# ==============================================================================
# finalize-archive.sh - 归档收口（清理+校验+整合）
# 用法: ./scripts/finalize-archive.sh <软件名> <版本>
#
# 执行顺序:
#   [1] 清理临时文件（*.tmp, .bak）
#   [2] 生成/更新软件级 RELEASENOTE.md（聚合多版本）
#   [3] 必填文件完整性校验（含软件级 + 版本级）
#   [4] 信息一致性检查
#   [5] 最终报告

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVES_DIR="${PROJECT_DIR}/archives"

# ---- 临时文件清理 trap ----
_TMP_FILES=""
_cleanup_tmp() {
    # shellcheck disable=SC2086
    rm -f $_TMP_FILES
}
trap '_cleanup_tmp; exit $?' EXIT INT TERM
_mktmp() {
    _mt_p="${TMPDIR:-$HOME/tmp}/finalize_$$_${1}.$$"
    : > "$_mt_p" 2>/dev/null || _mt_p="/tmp/finalize_$$_${1}.$$"
    : > "$_mt_p"
    _TMP_FILES="$_TMP_FILES $_mt_p"
    printf '%s' "$_mt_p"
}

if [ $# -lt 2 ]; then
    echo "❌ 用法: $0 <软件名> <版本>"
    exit 1
fi

SOFTWARE_NAME="$1"
VERSION="$2"

# ---------- 路径遍历防护 ----------
sanitize_path_component() {
    echo "$1" | sed 's/[^a-zA-Z0-9._+-]//g'
}
SOFTWARE_NAME=$(sanitize_path_component "$SOFTWARE_NAME")
VERSION=$(sanitize_path_component "$VERSION")
FIRST_LETTER="$(echo "$SOFTWARE_NAME" | cut -c1 | tr 'A-Z' 'a-z')"
SOFTWARE_DIR="${ARCHIVES_DIR}/${FIRST_LETTER}/${SOFTWARE_NAME}"
VERSION_DIR="${SOFTWARE_DIR}/${VERSION}"

echo "════════════════════════════════════════"
echo "  归档收口: ${SOFTWARE_NAME} ${VERSION}"
echo "  软件目录: ${SOFTWARE_DIR}"
echo "  版本目录: ${VERSION_DIR}"
echo "════════════════════════════════════════"
echo ""

if [ ! -d "$VERSION_DIR" ]; then
    echo "❌ 版本目录不存在: $VERSION_DIR"
    exit 1
fi

# ============================================================
# 阶段 1: 清理临时文件和垃圾
# ============================================================
echo "[1/5] 清理临时文件..."

_tmp_count=0; _bak_count=0

for _sub in "" patches reports scripts logs packaging; do
    [ -n "$_sub" ] && _target="${VERSION_DIR}/${_sub}" || _target="$VERSION_DIR"
    [ ! -d "$_target" ] && continue
    # [FIX#5] 原: for _f in $(ls -1a "$_target"/*.tmp) — word-split 反模式
    # 改为安全的 glob 循环，文件名含空格不再崩溃
    for _f in "$_target"/*.tmp; do
        [ -e "$_f" ] || continue
        rm -f "$_f" 2>/dev/null; _tmp_count=$((_tmp_count + 1))
    done
    # [FIX#5] 同上, .bak 文件
    for _f in "$_target"/*.bak; do
        [ -e "$_f" ] || continue
        rm -f "$_f" 2>/dev/null; _bak_count=$((_bak_count + 1))
    done
done

_DEBUG_DIR="${VERSION_DIR}/packaging/debug"
if [ -d "$_DEBUG_DIR" ]; then
    # [FIX#5] 原: for _f in $(ls -1a "$_DEBUG_DIR") — word-split 反模式
    # 改为安全 glob 遍历目录内容
    for _f in "$_DEBUG_DIR"/*; do
        [ -e "$_f" ] || continue
        _fb="$(basename "$_f")"
        case "$_fb" in *.debug|.|..) continue ;; esac
        [ -f "$_f" ] && rm -f "$_f"
    done
fi

[ "$_tmp_count" -gt 0 ] && echo "  已删除 $_tmp_count 个 .tmp 文件"
[ "$_bak_count" -gt 0 ] && echo "  已删除 $_bak_count 个 .bak 文件"
[ "$_tmp_count" -eq 0 ] && [ "$_bak_count" -eq 0 ] && echo "  无需清理，目录干净"

# ============================================================
# 阶段 2: 生成/更新软件级 RELEASENOTE.md
# ============================================================
echo ""
echo "[2/5] 生成软件级 RELEASENOTE.md..."

_RN="${SOFTWARE_DIR}/RELEASENOTE.md"

_BSYS="unknown"; _SRC_URL=""

# 收集包内容统计
_BIN_COUNT=$(grep "^binary_count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")
_MAN_COUNT=$(grep "^man_page_count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")

# 收集排除列表
if grep -q "^exclude_list:" "${VERSION_DIR}/manifest.yaml"; then
    _EXCLUDE_COUNT=$(grep "^ *count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")
    _EXCLUDE_LIST=$(sed -n "/^exclude_list:/,/^patches:/p" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | grep "^ *-" | sed "s/^ *- //" | cut -d"#" -f1 | tr -s " " | tr "\n" "," | sed "s/,$//")
fi
if [ -f "${VERSION_DIR}/manifest.yaml" ]; then
    _BSYS=$(grep "build_system:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')
    [ -z "$_BSYS" ] && _BSYS="unknown"

# 收集包内容统计
_BIN_COUNT=$(grep "^binary_count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")
_MAN_COUNT=$(grep "^man_page_count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")

# 收集排除列表
if grep -q "^exclude_list:" "${VERSION_DIR}/manifest.yaml"; then
    _EXCLUDE_COUNT=$(grep "^ *count:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d " ")
fi
    _SRC_URL=$(grep "^source_url:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')
fi

_BIN_NAME="$SOFTWARE_NAME"; _PKG_FILENAME=""; _PKG_SIZE="未知"
if [ -d "${VERSION_DIR}/packaging" ]; then
    # [FIX#5] 原: for _f in $(ls -1 "${VERSION_DIR}/packaging/"*-ohos-aarch64.tar.gz)
    for _f in "${VERSION_DIR}/packaging/"*-ohos-aarch64.tar.gz; do
        [ -f "$_f" ] && _PKG_FILENAME="$(basename "$_f")" && break
    done
    [ -n "$_PKG_FILENAME" ] && _PKG_SIZE=$(du -h "${VERSION_DIR}/packaging/${_PKG_FILENAME}" 2>/dev/null | cut -f1)
    if [ -d "${VERSION_DIR}/packaging/bin" ]; then
        # [FIX#5] 原: _BN=$(ls -1 "${VERSION_DIR}/packaging/bin/" | head -1)
        # 改为安全 glob 取首个条目
        _BN=""
        for _bf in "${VERSION_DIR}/packaging/bin/"*; do
            [ -e "$_bf" ] && _BN="$(basename "$_bf")" && break
        done
        [ -n "$_BN" ] && _BIN_NAME="$_BN"
    fi
fi

_QUALITY="未执行"
_QR="${VERSION_DIR}/reports/quality-report.md"
[ -f "$_QR" ] && _QUALITY=$(grep -oE 'PASS|FAIL' "$_QR" 2>/dev/null | head -1)

_PATCHDIR="${VERSION_DIR}/patches"
_TOTAL_PATCHES=0
if [ -d "$_PATCHDIR" ]; then
    # [FIX#5] 原: _TOTAL_PATCHES=$(ls -1 "$_PATCHDIR"/000*.patch | wc -l)
    # 改为安全循环计数
    _tpc=0
    for _pf in "$_PATCHDIR"/000*.patch; do
        [ -f "$_pf" ] && _tpc=$((_tpc + 1))
    done
    _TOTAL_PATCHES=$_tpc
fi

# 收集已有版本列表（用于聚合显示）— 需要 sort -V，使用临时文件
_VERSION_LIST=""
if [ -d "$SOFTWARE_DIR" ]; then
    _vdlst=$(_mktmp verdirs)
    # [FIX#5] 原: for _vd in $(ls -1d "$SOFTWARE_DIR"/[0-9]* | sort -V)
    # 改为 find 输出到临时文件，sort 后读取
    find "$SOFTWARE_DIR" -maxdepth 1 -type d -name '[0-9]*' > "$_vdlst" 2>/dev/null || true
    if [ -s "$_vdlst" ]; then
        sort -V "$_vdlst" > "${_vdlst}.sorted" 2>/dev/null || sort -t'/' -k6 -n "$_vdlst" > "${_vdlst}.sorted" 2>/dev/null
        while IFS= read -r _vd; do
            [ -d "$_vd" ] || continue
            _v=$(basename "$_vd")
            [ -f "$_vd/manifest.yaml" ] && _VERSION_LIST="${_VERSION_LIST}${_v} "
        done < "${_vdlst}.sorted"
        rm -f "${_vdlst}.sorted"
    fi
fi

# --- 分段生成软件级 RELEASENOTE.md ---
cat > "$_RN" << EOF
# ${SOFTWARE_NAME} — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速安装

\`\`\`bash
tar xzf ${_PKG_FILENAME:-$SOFTWARE_NAME-$VERSION-ohos-aarch64.tar.gz} -C ~/usr/local/
~/usr/local/bin/cat --version
\`\`\`

或使用 install.sh 一键安装：
\`\`\`bash
sh install-${SOFTWARE_NAME}-${VERSION}.sh
\`\`\`

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
EOF

# 追加版本表（动态）
if [ -d "$SOFTWARE_DIR" ]; then
    _vdlst2=$(_mktmp verdirs2)
    find "$SOFTWARE_DIR" -maxdepth 1 -type d -name '[0-9]*' > "$_vdlst2" 2>/dev/null || true
    if [ -s "$_vdlst2" ]; then
        sort -Vr "$_vdlst2" > "${_vdlst2}.sorted" 2>/dev/null || sort -t'/' -k6 -nr "$_vdlst2" > "${_vdlst2}.sorted" 2>/dev/null
        while IFS= read -r _vd; do
            [ -d "$_vd" ] || continue
            _v=$(basename "$_vd")
            _st="unknown"; _pc=0
            [ -f "$_vd/manifest.yaml" ] && _st=$(grep "^status:" "$_vd/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d ' ')
            if [ -d "$_vd/patches" ]; then
                _tpc2=0
                for _pf2 in "$_vd"/patches/"000"*.patch; do
                    [ -f "$_pf2" ] && _tpc2=$((_tpc2 + 1))
                done
                _pc=$_tpc2
            fi
            echo "| ${_v} | ${_st} | ${_pc} |" >> "$_RN"
        done < "${_vdlst2}.sorted"
        rm -f "${_vdlst2}.sorted"
    fi
fi

# 追加当前版本详情（静态部分）
cat >> "$_RN" << EOF

## 当前版本 (${VERSION}) 详情

### 包内容

| 项目 | 数量 |
|------|------|
| 二进制 (bin/) | ${_BIN_COUNT:-未知} 个 ELF aarch64，已签名 |
| 手册页 | ${_MAN_COUNT:-未知} 个 |
| 主包大小 | ${_PKG_SIZE:-未知} |
EOF

# 追加排除列表（条件）
if [ -n "$_EXCLUDE_LIST" ] && [ "${_EXCLUDE_COUNT:-0}" -gt 0 ]; then
    cat >> "$_RN" << EXCLEOF

### 排除命令 (${_EXCLUDE_COUNT} 个)

以下命令因平台限制未包含，请使用系统 **toybox** 替代：

\`\`\`
${_EXCLUDE_LIST}
\`\`\`
EXCLEOF
fi

# 追加编译信息 + 补丁列表（静态部分）
cat >> "$_RN" << EOF

### 编译信息

| 项目 | 值 |
|------|-----|
| 构建系统 | ${_BSYS} |
| 编译器 | clang + musl libc (HarmonyOS NDK) |
| 目标 | aarch64-unknown-linux-ohos |
| 补丁 | ${_TOTAL_PATCHES} 个 |

### 补丁列表
EOF

# 追加补丁列表（动态）
if [ "$_TOTAL_PATCHES" -gt 0 ]; then
    for _p in "${VERSION_DIR}/patches/"000*.patch; do
        [ -f "$_p" ] && echo "- ✅ $(basename "$_p")" >> "$_RN"
    done
else
    echo "- 无补丁（原生兼容）" >> "$_RN"
fi

# 追加尾部（静态）
cat >> "$_RN" << EOF

## 环境要求

- **平台**: HarmonyOS / OpenHarmony, aarch64
- **依赖**: musl libc（系统自带）

## 许可证

见原始上游源码

---
*由 finalize-archive.sh 自动生成 · $(date '+%Y-%m-%d %H:%M')*
EOF

echo "  OK 软件级 RELEASENOTE.md ($(wc -l < "$_RN" | tr -d ' ') 行)"

echo "  OK 软件级 RELEASENOTE.md ($(wc -l < "$_RN" | tr -d ' ') 行)"

# ============================================================
# 阶段 3: 必填文件完整性校验
# ============================================================
echo ""
echo "[3/5] 必填文件完整性校验..."

_MISSING=0

# 3a: 软件级必填文件
for _file in README.md RELEASENOTE.md install.sh; do
    if [ -f "${SOFTWARE_DIR}/${_file}" ]; then
        _lines=$(wc -l < "${SOFTWARE_DIR}/${_file}" | tr -d ' ')
        if [ "$_lines" -lt 5 ]; then
            echo "  WARN 软件级 ${_file} 存在但内容过短 (${_lines} 行)"
            _MISSING=$((_MISSING + 1))
        else
            echo "  OK 软件级 ${_file} (${_lines} 行)"
        fi
    else
        echo "  FAIL 软件级 ${_file} 缺失!"
        _MISSING=$((_MISSING + 1))
    fi
done

# 3b: 版本级必填文件
for _file in manifest.yaml PROGRESS.md; do
    if [ -f "${VERSION_DIR}/${_file}" ]; then
        _lines=$(wc -l < "${VERSION_DIR}/${_file}" | tr -d ' ')
        if [ "$_lines" -lt 5 ]; then
            echo "  WARN 版本级 ${_file} 过短 (${_lines} 行)"
            _MISSING=$((_MISSING + 1))
        else
            echo "  OK 版本级 ${_file} (${_lines} 行)"
        fi
    else
        echo "  FAIL 版本级 ${_file} 缺失!"
        _MISSING=$((_MISSING + 1))
    fi
done

# 3c: 版本级必填目录
for _dir in patches reports packaging; do
    if [ -d "${VERSION_DIR}/${_dir}" ]; then
        echo "  OK 版本级 ${_dir}/"
    else
        echo "  FAIL 版本级 ${_dir}/ 缺失!"
        _MISSING=$((_MISSING + 1))
    fi
done

# 3d: packaging 交付物检查
_status="unknown"
[ -f "${VERSION_DIR}/manifest.yaml" ] && _status=$(grep "^status:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d ' ')

if [ "$_status" = "success" ] || [ "$_status" = "partial" ]; then
    _PKGDIR="${VERSION_DIR}/packaging"
    _has_release=0
    # [FIX#5] 原: for _f in $(ls -1 "$_PKGDIR"/*-ohos-aarch64.tar.gz)
    for _f in "$_PKGDIR"/*-ohos-aarch64.tar.gz; do
        [ -f "$_f" ] && _has_release=1 && break
    done
    _has_debug=0
    # [FIX#5] 原: for _f in $(ls -1 "$_PKGDIR"/*-ohos-aarch64-debug.tar.gz)
    for _f in "$_PKGDIR"/*-ohos-aarch64-debug.tar.gz; do
        [ -f "$_f" ] && _has_debug=1 && break
    done
    
    [ "$_has_release" -eq 0 ] && echo "  FAIL packaging/ 缺少 release tar.gz" && _MISSING=$((_MISSING + 1)) || echo "  OK packaging/release.tar.gz"
    [ "$_has_debug" -eq 0 ] && echo "  WARN packaging/ 缺少 debug tar.gz" || echo "  OK packaging/debug.tar.gz"
else
    echo "  SKIP packaging/ 检查 (status=$_status)"
fi

# ============================================================
# 阶段 4: 信息一致性检查
# ============================================================
echo ""
echo "[4/5] 信息一致性检查..."

_issues=0

_prog_status=""; _manifest_status=""
[ -f "${VERSION_DIR}/PROGRESS.md" ] && _prog_status=$(grep -oE 'success#final|success|partial|failed|compiling' "${VERSION_DIR}/PROGRESS.md" 2>/dev/null | head -1)
[ -f "${VERSION_DIR}/manifest.yaml" ] && _manifest_status=$(grep "^status:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d ' ')

if [ -n "$_prog_status" ] && [ -n "$_manifest_status" ]; then
    if [ "$_prog_status" != "$_manifest_status" ]; then
        echo "  WARN 状态不一致: PROGRESS=$_prog_status vs manifest=$_manifest_status"
        _issues=$((_issues + 1))
    else
        echo "  OK 状态一致: $_manifest_status"
    fi
else
    echo "  SKIP 无法比对状态"
fi

_patch_in_manifest=0
[ -f "${VERSION_DIR}/manifest.yaml" ] && { _c=$(grep -c 'file: ".*\.patch"' "${VERSION_DIR}/manifest.yaml" 2>/dev/null) && _patch_in_manifest="$_c" || true; }

if [ "$_patch_in_manifest" -ne "$_TOTAL_PATCHES" ]; then
    echo "  WARN 补丁数量不一致: manifest=$_patch_in_manifest vs 磁盘=$_TOTAL_PATCHES"
    _issues=$((_issues + 1))
else
    echo "  OK 补丁数量一致: ${_TOTAL_PATCHES} 个"
fi

_dialog_sections=0
[ -f "${VERSION_DIR}/PROGRESS.md" ] && { _c=$(grep -c "^### 对话 #" "${VERSION_DIR}/PROGRESS.md" 2>/dev/null) && _dialog_sections="$_c" || true; }
if [ "$_dialog_sections" -eq 0 ]; then
    echo "  WARN PROGRESS.md 无对话记录"
    _issues=$((_issues + 1))
else
    echo "  OK PROGRESS.md 有 ${_dialog_sections} 轮对话记录"
fi

# ============================================================
# 阶段 5: 最终报告
# ============================================================
echo ""
echo "[5/5] 收口报告"
echo "════════════════════════════════════════"

_TOTAL_REPORTS=0
_RPTDIR="${VERSION_DIR}/reports"
if [ -d "$_RPTDIR" ]; then
    # [FIX#5] 原: _TOTAL_REPORTS=$(ls -1 "$_RPTDIR"/*.md | wc -l)
    _rc=0
    for _rf in "$_RPTDIR"/*.md; do
        [ -f "$_rf" ] && _rc=$((_rc + 1))
    done
    _TOTAL_REPORTS=$_rc
fi

_TOTAL_PKGS=0
_PKGDIR="${VERSION_DIR}/packaging"
if [ -d "$_PKGDIR" ]; then
    # [FIX#5] 原: _TOTAL_PKGS=$(ls -1 "$_PKGDIR"/*.tar.gz | wc -l)
    _kc=0
    for _kf in "$_PKGDIR"/*.tar.gz; do
        [ -f "$_kf" ] && _kc=$((_kc + 1))
    done
    _TOTAL_PKGS=$_kc
fi

echo "  软件:       ${SOFTWARE_NAME} ${VERSION}"
echo "  状态:       ${_manifest_status:-unknown}"
echo "  补丁:       ${_TOTAL_PATCHES} 个"
echo "  报告:       ${_TOTAL_REPORTS} 个"
echo "  打包产物:   ${_TOTAL_PKGS} 个"
echo "  一致性问题: ${_issues} 个"
echo "  缺失项:     ${_MISSING} 个"

if [ "$_MISSING" -gt 0 ] || [ "$_issues" -gt 0 ]; then
    echo ""
    echo "归档存在问题，建议修复后再标记完成"
    [ "$_MISSING" -gt 0 ] && echo "  -> 缺失 $_MISSING 个必填文件/目录"
    [ "$_issues" -gt 0 ] && echo "  -> 存在 $_issues 个一致性问题"
    exit 2
else
    echo ""
    echo "OK 归档收口通过，可以安全关闭"
    exit 0
fi
