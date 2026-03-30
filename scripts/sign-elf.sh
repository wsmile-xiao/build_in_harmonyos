#!/bin/sh
# sign-elf.sh - 鸿蒙 ELF 文件签名（四步流程）
# 用法: ./sign-elf.sh <ELF文件> [RPATH路径]
#       ./sign-elf.sh --batch <目录>
#
# 鸿蒙系统要求 ELF 文件必须签名才能运行。
# 修改 ELF（如 patchelf 设置 RPATH）后签名会失效，需要重新签名。
#
# 四步流程：
#   1. patchelf --set-rpath（可选）
#   2. llvm-objcopy --remove-section .codesign
#   3. binary-sign-tool sign
#   4. chmod a+x
#   5. 验证 RUNPATH（如果设了 RPATH）

set -e

# ============ 工具路径配置（可按需修改） ============
HNP_BIN="/data/service/hnp/bin"
LLVM_OBJCOPY="${HNP_BIN}/llvm-objcopy"
BINARY_SIGN_TOOL="${HNP_BIN}/binary-sign-tool"
LLVM_READELF="${HNP_BIN}/llvm-readelf"
PATCHELF="patchelf"
# ===================================================

SCRIPT_NAME="$(basename "$0")"

show_help() {
    cat <<'HELPEOF'
用法:
  ./sign-elf.sh <ELF文件> [RPATH路径]       签名单个 ELF 文件
  ./sign-elf.sh --batch <目录>              批量签名目录下所有 ELF 文件

描述:
  对鸿蒙系统下的 ELF 文件执行四步签名流程：
  1. (可选) patchelf --set-rpath 设置 RPATH/RUNPATH
  2. llvm-objcopy --remove-section .codesign 移除旧签名
  3. binary-sign-tool sign 重新签名
  4. chmod a+x 恢复可执行权限
  5. (可选) llvm-readelf -d | grep RUNPATH 验证 RPATH

参数:
  <ELF文件>    要签名的 ELF 二进制文件路径
  [RPATH路径]  要设置的 RPATH 路径（可选）
  --batch <目录>  批量模式，递归处理目录下所有 ELF 文件

工具路径（在脚本顶部可配置）:
  LLVM_OBJCOPY       = ${LLVM_OBJCOPY}
  BINARY_SIGN_TOOL   = ${BINARY_SIGN_TOOL}
  LLVM_READELF       = ${LLVM_READELF}
  PATCHELF           = ${PATCHELF}

示例:
  ./sign-elf.sh /path/to/mybinary
  ./sign-elf.sh /path/to/mybinary /data/service/hnp/lib
  ./sign-elf.sh --batch /path/to/libs/

退出码:
  0  成功
  1  参数错误
  2  工具缺失
  3  签名失败
HELPEOF
    exit 0
}

# ---------- 工具检查 ----------
check_tools() {
    missing=""
    if ! command -v "$PATCHELF" >/dev/null 2>&1; then
        missing="${missing}  patchelf\n"
    fi
    if [ ! -x "$LLVM_OBJCOPY" ]; then
        missing="${missing}  ${LLVM_OBJCOPY}\n"
    fi
    if [ ! -x "$BINARY_SIGN_TOOL" ]; then
        missing="${missing}  ${BINARY_SIGN_TOOL}\n"
    fi
    if [ ! -x "$LLVM_READELF" ]; then
        missing="${missing}  ${LLVM_READELF}\n"
    fi
    if [ -n "$missing" ]; then
        echo "❌ 以下工具缺失，无法继续："
        printf "%b" "$missing"
        exit 2
    fi
}

# ---------- 检查是否为 ELF 文件 ----------
is_elf() {
    _file="$1"
    [ -f "$_file" ] && head -c 4 "$_file" 2>/dev/null | grep -q '\x7fELF'
}

# ---------- 签名单个文件 ----------
sign_single_elf() {
    _elf_file="$1"
    _rpath="$2"

    if [ ! -f "$_elf_file" ]; then
        echo "❌ 文件不存在: $_elf_file"
        return 1
    fi

    if ! is_elf "$_elf_file"; then
        echo "⚠️  跳过（非 ELF 文件）: $_elf_file"
        return 0
    fi

    echo "────────────────────────────"
    echo "📝 处理: $_elf_file"

    # 步骤 0（可选）: 设置 RPATH
    if [ -n "$_rpath" ]; then
        echo "  [1/5] 设置 RPATH: $_rpath"
        if "$PATCHELF" --set-rpath "$_rpath" "$_elf_file"; then
            echo "  ✅ RPATH 设置成功"
        else
            echo "  ❌ RPATH 设置失败"
            return 3
        fi
    fi

    # 步骤 1: 移除旧签名
    _step_num="1"
    [ -n "$_rpath" ] && _step_num="2"
    echo "  [${_step_num}/5] 移除旧签名 (.codesign)"
    if "$LLVM_OBJCOPY" --remove-section .codesign "$_elf_file"; then
        echo "  ✅ 旧签名已移除"
    else
        echo "  ❌ 移除旧签名失败"
        return 3
    fi

    # 步骤 2: 重新签名
    _step_num=$(( _step_num + 1 ))
    echo "  [${_step_num}/5] 执行 binary-sign-tool 签名"
    _tmp_out="${_elf_file}.signed.tmp"
    if "$BINARY_SIGN_TOOL" sign -inFile "$_elf_file" -outFile "$_tmp_out" -selfSign 1; then
        mv -f "$_tmp_out" "$_elf_file"
        echo "  ✅ 签名成功"
    else
        rm -f "$_tmp_out"
        echo "  ❌ 签名失败"
        return 3
    fi

    # 步骤 3: 恢复权限
    _step_num=$(( _step_num + 1 ))
    echo "  [${_step_num}/5] 恢复可执行权限"
    if chmod a+x "$_elf_file"; then
        echo "  ✅ 权限已恢复"
    else
        echo "  ⚠️  权限设置失败"
    fi

    # 步骤 4（可选）: 验证 RPATH
    _step_num=$(( _step_num + 1 ))
    if [ -n "$_rpath" ]; then
        echo "  [${_step_num}/5] 验证 RUNPATH"
        _runpath="$("$LLVM_READELF" -d "$_elf_file" 2>/dev/null | grep -o 'RUNPATH[[:space:]]*\[[^]]*\]' | head -1)"
        if [ -n "$_runpath" ]; then
            echo "  ✅ RUNPATH 验证通过: $_runpath"
        else
            echo "  ⚠️  未检测到 RUNPATH，可能设置未生效"
        fi
    else
        echo "  [${_step_num}/5] 跳过 RPATH 验证（未指定 RPATH）"
    fi

    echo "  ✅ 签名流程完成: $_elf_file"
    return 0
}

# ---------- 批量处理 ----------
batch_sign() {
    _dir="$1"

    if [ ! -d "$_dir" ]; then
        echo "❌ 目录不存在: $_dir"
        exit 1
    fi

    echo "📦 批量模式: $_dir"
    echo ""

    _total=0
    _success=0
    _failed=0
    _skipped=0

    # 使用 find 递归查找 ELF 文件
    # 注意：POSIX find 不支持 -print0，使用换行分隔
    find "$_dir" -type f 2>/dev/null | while read -r _f; do
        _total=$(( _total + 1 ))
        if is_elf "$_f"; then
            if sign_single_elf "$_f" ""; then
                _success=$(( _success + 1 ))
            else
                _failed=$(( _failed + 1 ))
            fi
        else
            _skipped=$(( _skipped + 1 ))
        fi
    done

    echo ""
    echo "════════════════════════════"
    echo "📊 批量处理完成"
    echo "  ✅ 成功: $_success"
    if [ "$_failed" -gt 0 ]; then
        echo "  ❌ 失败: $_failed"
    fi
    if [ "$_skipped" -gt 0 ]; then
        echo "  ⏭️  跳过（非 ELF）: $_skipped"
    fi
    echo "════════════════════════════"

    if [ "$_failed" -gt 0 ]; then
        return 3
    fi
    return 0
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
    --batch)
        if [ $# -lt 2 ]; then
            echo "❌ --batch 需要指定目录参数。"
            exit 1
        fi
        check_tools
        batch_sign "$2"
        exit $?
        ;;
    -*)
        echo "❌ 未知参数: $1。使用 --help 查看帮助。"
        exit 1
        ;;
    *)
        check_tools
        sign_single_elf "$1" "${2:-}"
        exit $?
        ;;
esac
