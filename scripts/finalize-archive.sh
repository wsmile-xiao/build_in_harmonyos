#!/bin/sh
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

if [ $# -lt 2 ]; then
    echo "❌ 用法: $0 <软件名> <版本>"
    exit 1
fi

SOFTWARE_NAME="$1"
VERSION="$2"
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
    for _f in $(ls -1a "$_target"/*.tmp 2>/dev/null); do
        [ -z "$_f" ] && continue
        rm -f "$_target/$(basename "$_f")" 2>/dev/null; _tmp_count=$((_tmp_count + 1))
    done
    for _f in $(ls -1a "$_target"/*.bak 2>/dev/null); do
        [ -z "$_f" ] && continue
        rm -f "$_target/$(basename "$_f")" 2>/dev/null; _bak_count=$((_bak_count + 1))
    done
done

_DEBUG_DIR="${VERSION_DIR}/packaging/debug"
if [ -d "$_DEBUG_DIR" ]; then
    for _f in $(ls -1a "$_DEBUG_DIR" 2>/dev/null); do
        case "$_f" in *.debug|.|..) continue ;; esac
        [ -f "$_DEBUG_DIR/$_f" ] && rm -f "$_DEBUG_DIR/$_f"
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
if [ -f "${VERSION_DIR}/manifest.yaml" ]; then
    _BSYS=$(grep "^build_system:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')
    [ -z "$_BSYS" ] && _BSYS="unknown"
    _SRC_URL=$(grep "^source_url:" "${VERSION_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')
fi

_BIN_NAME="$SOFTWARE_NAME"; _PKG_FILENAME=""; _PKG_SIZE="未知"
if [ -d "${VERSION_DIR}/packaging" ]; then
    for _f in $(ls -1 "${VERSION_DIR}/packaging/"*-ohos-aarch64.tar.gz 2>/dev/null); do
        [ -f "$_f" ] && _PKG_FILENAME="$(basename "$_f")" && break
    done
    [ -n "$_PKG_FILENAME" ] && _PKG_SIZE=$(du -h "${VERSION_DIR}/packaging/${_PKG_FILENAME}" 2>/dev/null | cut -f1)
    if [ -d "${VERSION_DIR}/packaging/bin" ]; then
        _BN=$(ls -1 "${VERSION_DIR}/packaging/bin/" 2>/dev/null | head -1)
        [ -n "$_BN" ] && _BIN_NAME="$_BN"
    fi
fi

_QUALITY="未执行"
_QR="${VERSION_DIR}/reports/quality-report.md"
[ -f "$_QR" ] && _QUALITY=$(grep -oE 'PASS|FAIL' "$_QR" 2>/dev/null | head -1)

_PATCHDIR="${VERSION_DIR}/patches"
_TOTAL_PATCHES=0
[ -d "$_PATCHDIR" ] && _TOTAL_PATCHES=$(ls -1 "$_PATCHDIR"/000*.patch 2>/dev/null | wc -l | tr -d ' ')

# 收集已有版本列表（用于聚合显示）
_VERSION_LIST=""
for _vd in $(ls -1d "$SOFTWARE_DIR"/[0-9]* 2>/dev/null | sort -V); do
    _v=$(basename "$_vd")
    [ -f "$_vd/manifest.yaml" ] && _VERSION_LIST="${_VERSION_LIST}${_v} "
done

cat > "$_RN" <<RNEOF
# ${SOFTWARE_NAME} — HarmonyOS aarch64 预编译包

> **一行安装，开箱即用。** 从源码编译，适配鸿蒙系统。

## 快速使用

从 [cmd-pkgs releases](https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases) 下载对应版本的 tar.gz，解压到 ~/usr/local/ 即可使用。

## 可用版本

| 版本 | 状态 | 补丁数 | 质量门禁 |
|------|------|--------|---------|
$(for _vd in $(ls -1d "$SOFTWARE_DIR"/[0-9]* 2>/dev/null | sort -Vr); do
    _v=$(basename "$_vd")
    _st="unknown"; _pc=0; _ql="--"
    [ -f "$_vd/manifest.yaml" ] && _st=$(grep "^status:" "$_vd/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2 | tr -d ' ')
    [ -d "$_vd/patches" ] && _pc=$(ls -1 "$_vd"/patches/000*.patch 2>/dev/null | wc -l | tr -d ' ')
    [ -f "$_vd/reports/quality-report.md" ] && _ql=$(grep -oE 'PASS|FAIL' "$_vd/reports/quality-report.md" 2>/dev/null | head -1)
    echo "| ${_v} | ${_st} | ${_pc} | ${_ql:-未测} |"
done)

## 当前版本 (${VERSION}) 详情

### 包含内容

| 内容 | 数量/大小 | 说明 |
|------|----------|------|
| 主二进制 bin/${_BIN_NAME} | ELF aarch64, 已签名 | 核心程序 |
| Debug 符号包 | 独立下载 | GDB 调试用 |

### 环境要求

- **平台**: HarmonyOS (OpenHarmony) aarch64
- **依赖**: 仅 musl libc（系统自带，无需额外安装）
- **磁盘**: ~${_PKG_SIZE}（解压后）

### 编译信息

| 项目 | 值 |
|------|-----|
| 源码 | ${_SRC_URL:-见 manifest.yaml} |
| 构建系统 | $_BSYS |
| 编译器 | clang + musl libc |
| 目标 triplet | aarch64-unknown-linux-ohos |
| 补丁数 | ${_TOTAL_PATCHES} 个 |
| 质量门禁 | ${_QUALITY} |

### 已知适配

$(if [ "$_TOTAL_PATCHES" -gt 0 ]; then
    for _p in $(ls -1 "${VERSION_DIR}/patches/"000*.patch 2>/dev/null); do
        [ -f "$_p" ] && echo "- ✅ $(basename "$_p")"
    done
else
    echo "- 无补丁（原生兼容）"
fi)

### 安装说明

1. 从 releases 页面下载 \`${_PKG_FILENAME}\`
2. 解压到目标目录: tar xzf <文件> -C ~/usr/local/
3. 修复权限: chmod +x ~/usr/local/bin/*
4. 验证: \${_BIN_NAME} --version → \${VERSION}

> 或使用同目录下的 install.sh 一键安装（支持参数化版本选择）

## 许可证

见原始上游源码（许可证不变）

---
*由 finalize-archive.sh 自动生成 · $(date '+%Y-%m-%d %H:%M')*
RNEOF

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
    for _f in $(ls -1 "$_PKGDIR"/*-ohos-aarch64.tar.gz 2>/dev/null); do
        [ -f "$_f" ] && _has_release=1 && break
    done
    _has_debug=0
    for _f in $(ls -1 "$_PKGDIR"/*-ohos-aarch64-debug.tar.gz 2>/dev/null); do
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
[ -f "${VERSION_DIR}/PROGRESS.md" ] && _prog_status=$(grep -oE 'success|partial|failed|compiling' "${VERSION_DIR}/PROGRESS.md" 2>/dev/null | head -1)
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
[ -d "$_RPTDIR" ] && _TOTAL_REPORTS=$(ls -1 "$_RPTDIR"/*.md 2>/dev/null | wc -l | tr -d ' ')

_TOTAL_PKGS=0
_PKGDIR="${VERSION_DIR}/packaging"
[ -d "$_PKGDIR" ] && _TOTAL_PKGS=$(ls -1 "$_PKGDIR"/*.tar.gz 2>/dev/null | wc -l | tr -d ' ')

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
