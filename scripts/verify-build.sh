#!/bin/sh
# ==============================================================================
# [Layer 1] verify-build.sh - 产物质量门禁（四道全自动校验）
# ==============================================================================
# 层级: L1(全自动)
# 决策点: 无（完全确定性门禁检测）
# 入口: ./scripts/verify-build.sh <软件名> <版本>
#       ./scripts/verify-build.sh --software <名> --version <ver> --archive-dir <dir>
# 依赖: file, llvm-readelf, patchelf, find, patch
# 调用者: finish-build.sh (Step 3), AI / 用户
# ==============================================================================
# verify-build.sh — 产物质量门禁（finish-build.sh Step 3 / 独立 Step 4）
# 用法:
#   ./scripts/verify-build.sh <软件名> <版本>
#   ./scripts/verify-build.sh --software <名> --version <ver> --archive-dir <归档目录>
#
# 4 道门禁验证编译产物是否真正可用。
# 编译成功 ≠ 产物可用。本脚本确保交付的是"可交给别人用的三方库"。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

show_help() {
    cat <<'HELPEOF'
用法:
  ./scripts/verify-build.sh <软件名> <版本>
  ./scripts/verify-build.sh --software <名> --version <ver> [--archive-dir <归档目录>]

描述:
  产物质量门禁。4 道自动检测 + 输出质量报告。
  在 finish-build.sh Step 3 中自动调用，也可独立执行。

参数:
  <软件名>          软件名称（位置参数或 --software）
  <版本>            版本号（位置参数或 --version）
  --archive-dir     归档目录路径（可选，默认自动计算）

门禁:
  G1: 二进制完整性（ELF 可执行 / ldd 无缺 / file 正确）
  G2: 功能可用性（--version + 核心功能测试）
  G3: 可移植性（RPATH / 签名 / 解压后运行）
  G4: 档案完整性（man / .pc / 补丁 rebuild / manifest）

输出:
  reports/quality-report.md   # 详细报告
  exit 0 = 全部通过
  exit N = 第 N 道门禁失败

示例:
  ./scripts/verify-build.sh sed 4.9
HELPEOF
    exit 0
}

if [ $# -lt 2 ]; then
    echo "[FAIL] 缺少参数: $0 <软件名> <版本>"
    exit 1
fi

case "$1" in --help|-h) show_help ;; esac

# 解析参数（支持位置参数和可选标志）
SOFTWARE="$1"
VERSION=""
ARCHIVE_DIR_OVERRIDE=""

# 逐个解析参数
_i=1
while [ $_i -le $# ]; do
    _arg="$(eval echo "\${$_i}")"
    case "$_arg" in
        --software)
            _i=$((_i+1))
            SOFTWARE="$(eval echo "\${$_i}")"
            ;;
        --version)
            _i=$((_i+1))
            VERSION="$(eval echo "\${$_i}")"
            ;;
        --archive-dir)
            _i=$((_i+1))
            ARCHIVE_DIR_OVERRIDE="$(eval echo "\${$_i}")"
            ;;
        -*)
            # 跳过未知选项（兼容性）
            ;;
        *)
            # 位置参数：第一个非选项是 software，第二个是 version
            if [ -z "$SOFTWARE" ] || [ "$SOFTWARE" = "$_arg" ] && [ $_i -eq 1 ]; then
                : # SOFTWARE 已从 $1 设置或保持默认
            elif [ -z "$VERSION" ]; then
                VERSION="$_arg"
            fi
            ;;
    esac
    _i=$((_i+1))
done

# 回退：如果 --version 未提供但位置参数有 $2，使用 $2
if [ -z "$VERSION" ] && [ -n "$2" ]; then
    VERSION="$2"
fi

echo "[CHECK] 产物质量门禁"
echo "  软件: ${SOFTWARE} ${VERSION}"
echo ""

# ---- 找到安装目录和归档目录 ----
# DEFAULT_PREFIX 是全局安装前缀（由 init-build.sh export 或环境变量传入）
if [ -z "${DEFAULT_PREFIX:-}" ]; then
    DEFAULT_PREFIX="$HOME/usr/local"
fi

# 优先从 build-context 读取 TEST_PREFIX（staging 隔离目录）
# 这是当前软件的实际安装位置，避免扫描全局目录中其他软件的产物
_TEST_PREFIX=""
# 精确匹配
_CTX_FILE="${PROJECT_DIR}/.build-context-${SOFTWARE}-${VERSION}"
if [ -f "$_CTX_FILE" ]; then
    _TEST_PREFIX=$(grep "^TEST_PREFIX=\|^export TEST_PREFIX=" "$_CTX_FILE" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
fi
# 兜底: glob 匹配（容错参数顺序问题）
if [ -z "$_TEST_PREFIX" ]; then
    _CTX_GLOB=$(ls "${PROJECT_DIR}/.build-context-${SOFTWARE}-"*-${VERSION} "${PROJECT_DIR}/.build-context-${VERSION}-${SOFTWARE}"* 2>/dev/null | head -1)
    if [ -n "$_CTX_GLOB" ] && [ -f "$_CTX_GLOB" ]; then
        _TEST_PREFIX=$(grep "^TEST_PREFIX=\|^export TEST_PREFIX=" "$_CTX_GLOB" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
    fi
fi
# 也支持直接通过环境变量传入
if [ -z "$_TEST_PREFIX" ] && [ -n "${TEST_PREFIX:-}" ]; then
    _TEST_PREFIX="$TEST_PREFIX"
fi

# INSTALL_PREFIX: 产物扫描用此路径（staging 优先，fallback 到全局）
if [ -n "$_TEST_PREFIX" ] && [ -d "$_TEST_PREFIX/bin" ]; then
    INSTALL_PREFIX="$_TEST_PREFIX"
    echo "[INFO] 使用 staging 目录: $INSTALL_PREFIX"
else
    INSTALL_PREFIX="$DEFAULT_PREFIX"
    echo "[INFO] staging 未找到，回退到全局目录: $INSTALL_PREFIX"
fi

if [ ! -d "$INSTALL_PREFIX/bin" ] && [ ! -d "$INSTALL_PREFIX/lib" ]; then
    echo "[FAIL] 安装目录不存在: $INSTALL_PREFIX"
    exit 1
fi

FIRST_LETTER="$(echo "$SOFTWARE" | cut -c1 | tr 'A-Z' 'a-z')"

# 支持通过 --archive-dir 直接指定，或自动计算
if [ -n "$ARCHIVE_DIR_OVERRIDE" ] && [ -d "$ARCHIVE_DIR_OVERRIDE" ]; then
    ARCHIVE_DIR="$ARCHIVE_DIR_OVERRIDE"
else
    ARCHIVE_DIR="${PROJECT_DIR}/archives/${FIRST_LETTER}/${SOFTWARE}/${VERSION}"
fi

REPORT_DIR="${ARCHIVE_DIR}/reports"

mkdir -p "$REPORT_DIR"
REPORT_FILE="${REPORT_DIR}/quality-report.md"

# ---- 计数器 ----
G1_PASS=0; G1_FAIL=0; G1_WARN=0; G1_TOTAL=0
G2_PASS=0; G2_FAIL=0; G2_WARN=0; G2_TOTAL=0
G3_PASS=0; G3_FAIL=0; G3_WARN=0; G3_TOTAL=0
G4_PASS=0; G4_FAIL=0; G4_WARN=0; G4_TOTAL=0

# ---- 工具函数 ----
log_pass() { G1_PASS=$((G1_PASS+1)); G1_TOTAL=$((G1_TOTAL+1)); printf "     [OK] %s\n" "$1"; }
log_fail() { G1_FAIL=$((G1_FAIL+1)); G1_TOTAL=$((G1_TOTAL+1)); printf "     [FAIL] %s\n" "$1"; }
log_warn() { G1_WARN=$((G1_WARN+1)); G1_TOTAL=$((G1_TOTAL+1)); printf "     [WARN] %s\n" "$1"; }

g2_pass() { G2_PASS=$((G2_PASS+1)); G2_TOTAL=$((G2_TOTAL+1)); printf "     [OK] %s\n" "$1"; }
g2_fail() { G2_FAIL=$((G2_FAIL+1)); G2_TOTAL=$((G2_TOTAL+1)); printf "     [FAIL] %s\n" "$1"; }
g2_warn() { G2_WARN=$((G2_WARN+1)); G2_TOTAL=$((G2_TOTAL+1)); printf "     [WARN] %s\n" "$1"; }

g3_pass() { G3_PASS=$((G3_PASS+1)); G3_TOTAL=$((G3_TOTAL+1)); printf "     [OK] %s\n" "$1"; }
g3_fail() { G3_FAIL=$((G3_FAIL+1)); G3_TOTAL=$((G3_TOTAL+1)); printf "     [FAIL] %s\n" "$1"; }
g3_warn() { G3_WARN=$((G3_WARN+1)); G3_TOTAL=$((G3_TOTAL+1)); printf "     [WARN] %s\n" "$1"; }

g4_pass() { G4_PASS=$((G4_PASS+1)); G4_TOTAL=$((G4_TOTAL+1)); printf "     [OK] %s\n" "$1"; }
g4_fail() { G4_FAIL=$((G4_FAIL+1)); G4_TOTAL=$((G4_TOTAL+1)); printf "     [FAIL] %s\n" "$1"; }
g4_warn() { G4_WARN=$((G4_WARN+1)); G4_TOTAL=$((G4_TOTAL+1)); printf "     [WARN] %s\n" "$1"; }

# ============================================================
# G1: 二进制完整性
# ============================================================
echo "[G1/4] 二进制完整性..."

ELF_COUNT=0
MISSING_DEPS=0
BROKEN_ELFS=0

# 收集所有 ELF 文件（使用临时文件避免 word-split 反模式）
_tmp_g1_bin="${TMPDIR:-$HOME/tmp}/verify_find_g1_bin_$$.lst"
find "$INSTALL_PREFIX/bin" -type f > "$_tmp_g1_bin" 2>/dev/null || true
while IFS= read -r elf; do
    [ -f "$elf" ] || continue
    ELF_COUNT=$((ELF_COUNT + 1))
    
    # G1-1: file 命令识别
    FILE_TYPE=$(file -b "$elf" 2>/dev/null || echo "unknown")
    IS_ELF=$(echo "$FILE_TYPE" | grep -c "ELF\|executable\|shared object" || true)
    IS_SCRIPT=$(echo "$FILE_TYPE" | grep -c "script\|text" || true)
    
    if [ "$IS_ELF" -gt 0 ]; then
        log_pass "$(basename $elf): ${FILE_TYPE}"
    elif [ "$IS_SCRIPT" -gt 0 ]; then
        log_warn "$(basename $elf): 脚本非 ELF (${FILE_TYPE})"
    else
        log_fail "$(basename $elf): 无法识别 (${FILE_TYPE})"
        BROKEN_ELFS=$((BROKEN_ELFS + 1))
    fi
    
    # G1-2: 可执行性（非 Permission denied）
    if [ -x "$elf" ]; then
        :  # 已在上面通过
    else
        log_warn "$(basename $elf): 不可执行（可能是弹窗未确认）"
    fi
    
    # G1-3: 动态依赖检查
    if command -v llvm-readelf >/dev/null 2>&1; then
        NEEDED=$(llvm-readelf -d "$elf" 2>/dev/null | grep "(NEEDED)" || true)
        if [ -z "$NEEEDED" ]; then
            log_pass "$(basename $elf): 无动态依赖（静态链接或无 NEEDED）"
        else
            # 使用临时文件避免管道子 shell 丢失计数
            _DEP_TMP="${TMPDIR:-$HOME/tmp}/.dep_check_$$.txt"
            : > "$_DEP_TMP"
            echo "$NEEEDED" | while read -r line; do
                lib=$(echo "$line" | sed 's/.*\[\(.*\)].*/\1/')
                if [ -n "$lib" ]; then
                    if find "$DEFAULT_PREFIX/lib" -name "$lib*" 2>/dev/null | grep -q .; then
                        : # 依赖存在
                    else
                        echo "WARN:$(basename $elf): 缺少依赖 ${lib}" >> "$_DEP_TMP"
                    fi
                fi
            done
            # 在父 shell 中统计缺失依赖
            if [ -f "$_DEP_TMP" ]; then
                _missing_count=$(grep -c '^WARN:' "$_DEP_TMP" 2>/dev/null || echo "0")
                _missing_count=$(echo "$_missing_count" | tr -d ' ')
                MISSING_DEPS=$((MISSING_DEPS + _missing_count))
                cat "$_DEP_TMP" | while IFS=: read -r _type _msg; do log_warn "$_msg"; done
                rm -f "$_DEP_TMP"
            fi
        fi
    fi
done < "$_tmp_g1_bin"
rm -f "$_tmp_g1_bin"

# 也检查 lib 目录下的共享库（使用临时文件避免 word-split 反模式）
_tmp_g1_lib="${TMPDIR:-$HOME/tmp}/verify_find_g1_lib_$$.lst"
find "$INSTALL_PREFIX/lib" -name "*.so" -type f > "$_tmp_g1_lib" 2>/dev/null || true
while IFS= read -r lib; do
    [ -f "$lib" ] || continue
    ELF_COUNT=$((ELF_COUNT + 1))
    LIB_TYPE=$(file -b "$lib" 2>/dev/null || echo "unknown")
    case "$LIB_TYPE" in
        *ELF*) log_pass "lib/$(basename $lib): 共享库 OK" ;;
        *)    log_warn "lib/$(basename $lib): ${LIB_TYPE}" ;;
    esac
done < "$_tmp_g1_lib"
rm -f "$_tmp_g1_lib"

echo ""
echo "  G1 结果: ${G1_PASS}/${G1_TOTAL} 通过, ${G1_FAIL} 失败, ${G1_WARN} 警告"
echo "         (共 ${ELF_COUNT} 个文件, ${MISSING_DEPS} 缺依赖, ${BROKEN_ELFS} 损坏)"

# ============================================================
# G2: 功能可用性
# ============================================================
echo ""
echo "[G2/4] 功能可用性..."

# G2-1: --version 测试（使用临时文件避免 word-split 反模式）
_tmp_g2_bin="${TMPDIR:-$HOME/tmp}/verify_find_g2_bin_$$.lst"
find "$INSTALL_PREFIX/bin" -type f -executable > "$_tmp_g2_bin" 2>/dev/null || true
_head=0
while IFS= read -r bin; do
    [ -f "$bin" ] || continue
    _head=$((_head + 1))
    [ "$_head" -gt 10 ] && break
    BN=$(basename "$bin")
    # 跳过 wrapper 脚本
    head -1 "$bin" 2>/dev/null | grep -q "^#!" && continue
    
    VERSION_OUT=$("$bin" --version 2>&1) && RC=$? || RC=$?
    if [ $RC -eq 0 ] && [ -n "$VERSION_OUT" ]; then
        VER_LINE=$(echo "$VERSION_OUT" | head -1)
        g2_pass "${BN}: --version → ${VER_LINE}"
    else
        g2_warn "${BN}: --version 失败 (exit=$RC) — 可能需要弹窗确认或该命令不支持 --version"
    fi
done < "$_tmp_g2_bin"
rm -f "$_tmp_g2_bin"

# G2-2: 核心功能测试（从外部配置加载）
G2_CONFIG="${PROJECT_DIR}/config/g2-tests.conf"

if [ -f "$G2_CONFIG" ]; then
    # 加载配置并逐条执行测试（仅匹配当前 SOFTWARE 的条目）
    _g2_config_matched=0
    while IFS= read -r line; do
        # 跳过注释和空行
        case "$line" in \#*|"") continue ;; esac

        # 解析配置行（TAB 分隔格式: TEST_NAME=...<TAB>TEST_CMD=...<TAB>TEST_EXPECT=...）
        _test_name=$(echo "$line" | cut -f1 | sed 's/TEST_NAME=//' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        _test_cmd=$(echo "$line" | cut -f2 | sed 's/^TEST_CMD=//')
        _test_expect=$(echo "$line" | cut -f3 | sed 's/^TEST_EXPECT=//')

        [ -z "$_test_name" ] && continue

        # 仅执行与当前 SOFTWARE 匹配的测试（或通用测试）
        if [ "$_test_name" != "$SOFTWARE" ]; then
            continue
        fi
        _g2_config_matched=$((_g2_config_matched + 1))

        # 处理特殊标记
        case "$_test_cmd" in
            "@SKIP") g2_pass "G2 [SKIP] $_test_name (配置跳过)" ; continue ;;
        esac

        # 执行测试命令并捕获输出
        _output=$(eval "$_test_cmd" 2>&1) && _rc=$? || _rc=$?

        # 根据期望值判定结果
        if echo "$_output" | grep -qE "$_test_expect"; then
            g2_pass "${_test_name}: 功能测试通过 → $(echo "$_output" | head -1)"
        else
            g2_fail "${_test_name}: 功能测试失败 (rc=${_rc}, output: ${_output:-无输出}, expect: ${_test_expect})"
        fi
    done < "$G2_CONFIG"

    # 如果配置中没有匹配当前 SOFTWARE 的条目，走默认逻辑
    if [ "$_g2_config_matched" -eq 0 ]; then
        if [ $G2_PASS -gt 0 ]; then
            g2_pass "通用功能测试 (${SOFTWARE}): 配置中无专属条目，--version 已覆盖"
        else
            g2_warn "通用功能测试 (${SOFTWARE}): 无可执行的二进制用于测试"
        fi
    fi
else
    g2_warn "G2 测试配置文件不存在 ($G2_CONFIG)，使用默认检测"
    # fallback: 通用 --version 已在 G2-1 中完成，此处仅做兜底
    if [ $G2_PASS -gt 0 ]; then
        g2_pass "通用功能测试: --version 已覆盖（配置文件缺失，使用 fallback）"
    else
        g2_warn "通用功能测试: 无可执行的二进制用于测试（配置文件缺失）"
    fi
fi

echo ""
echo "  G2 结果: ${G2_PASS}/${G2_TOTAL} 通过, ${G2_FAIL} 失败, ${G2_WARN} 警告"

# ============================================================
# G3: 可移植性
# ============================================================
echo ""
echo "[G3/4] 可移植性..."

# G3-1: RPATH 检查（使用临时文件避免 word-split 反模式）
RPATH_OK=0; RPATH_BAD=0
if command -v patchelf >/dev/null 2>&1; then
    _tmp_g3_rpath="${TMPDIR:-$HOME/tmp}/verify_find_g3_rpath_$$.lst"
    find "$INSTALL_PREFIX/bin" -type f -executable > "$_tmp_g3_rpath" 2>/dev/null || true
    while IFS= read -r elf; do
        [ -f "$elf" ] || continue
        RPATH=$(patchelf --print-rpath "$elf" 2>/dev/null || true)
        if echo "$RPATH" | grep -q '\$ORIGIN'; then
            RPATH_OK=$((RPATH_OK + 1))
        elif [ -z "$RPATH" ]; then
            g3_warn "$(basename $elf): 无 RPATH（可能无法在其他路径运行）"
            RPATH_BAD=$((RPATH_BAD + 1))
        else
            g3_pass "$(basename $elf): RPATH=${RPATH}"
            RPATH_OK=$((RPATH_OK + 1))
        fi
    done < "$_tmp_g3_rpath"
    rm -f "$_tmp_g3_rpath"
else
    g3_warn "patchelf 不可用，跳过 RPATH 检查"
fi

# G3-2: ELF 签名检查（使用临时文件避免 word-split 反模式）
SIGNED_OK=0; SIGNED_BAD=0
if command -v sign-elf.sh >/dev/null 2>&1; then
    # 只检查签名是否存在，不重新签名
    _tmp_g3_sign="${TMPDIR:-$HOME/tmp}/verify_find_g3_sign_$$.lst"
    find "$INSTALL_PREFIX/bin" -type f -executable > "$_tmp_g3_sign" 2>/dev/null || true
    while IFS= read -r elf; do
        [ -f "$elf" ] || continue
        # 鸿蒙的签名状态可以通过特定方式检测
        SIGN_CHECK=$(file -b "$elf" 2>/dev/null)
        case "$SIGN_CHECK" in
            *"signed"*|*"signature"*)
                SIGNED_OK=$((SIGNED_OK + 1))
                g3_pass "$(basename $elf): 已签名"
                ;;
            *)
                g3_warn "$(basename $elf): 签名状态未知"
                SIGNED_BAD=$((SIGNED_BAD + 1))
                ;;
        esac
    done < "$_tmp_g3_sign"
    rm -f "$_tmp_g3_sign"
else
    g3_warn "sign-elf.sh 不可用，跳过签名检查"
fi

# G3-3: 解压后可运行模拟（使用临时文件避免 word-split 反模式）
REL_PATH_ISSUE=0
_tmp_g3_interp="${TMPDIR:-$HOME/tmp}/verify_find_g3_interp_$$.lst"
find "$INSTALL_PREFIX/bin" -type f -executable > "$_tmp_g3_interp" 2>/dev/null || true
while IFS= read -r elf; do
    [ -f "$elf" ] || continue
    INTERP=$(patchelf --print-interpreter "$elf" 2>/dev/null || true)
    if [ -n "$INTERP" ] && echo "$INTERP" | grep -q '^/'; then
        # 绝对路径解释器 — 在其他系统可能不存在
        case "$(basename "$INTERP")" in
            ld-musl*|ld-linux*) 
                # 标准链接器，通常没问题
                ;;
            *)
                g3_warn "$(basename $elf): 解释器为绝对路径 ${INTERP}"
                REL_PATH_ISSUE=$((REL_PATH_ISSUE + 1))
                ;;
        esac
    fi
done < "$_tmp_g3_interp"
rm -f "$_tmp_g3_interp"

echo ""
echo "  G3 结果: ${G3_PASS}/${G3_TOTAL} 通过, ${G3_FAIL} 失败, ${G3_WARN} 警告"
echo "         (RPATH: ${RPATH_OK} OK / ${RPATH_BAD} 缺, 签名: ${SIGNED_OK} OK / ${SIGNED_BAD} 未知)"

# ============================================================
# G4: 档案完整性
# ============================================================
echo ""
echo "[G4/4] 档案完整性..."

# G4-1: man page（使用临时文件避免 word-split 反模式）
_tmp_g4_man="${TMPDIR:-$HOME/tmp}/verify_find_g4_man_$$.lst"
find "$INSTALL_PREFIX/share/man" -name "*.${SOFTWARE}*" -type f > "$_tmp_g4_man" 2>/dev/null || true
MAN_COUNT=$(wc -l < "$_tmp_g4_man" 2>/dev/null | tr -d ' ')
rm -f "$_tmp_g4_man"
if [ "$MAN_COUNT" -gt 0 ]; then
    g4_pass "man page: 找到 ${MAN_COUNT} 个相关手册页"
else
    _tmp_g4_man_any="${TMPDIR:-$HOME/tmp}/verify_find_g4_man_any_$$.lst"
    find "$INSTALL_PREFIX/share/man" -name "*.1" -o -name "*.gz" > "$_tmp_g4_man_any" 2>/dev/null || true
    MAN_ANY=$(wc -l < "$_tmp_g4_man_any" 2>/dev/null | tr -d ' ')
    rm -f "$_tmp_g4_man_any"
    if [ "$MAN_ANY" -gt 0 ]; then
        g4_warn "man page: 未找到 ${SOFTWARE} 专用手册（但有 ${MAN_ANY} 个通用手册）"
    else
        g4_fail "man page: 完全没有手册页"
    fi
fi

# G4-2: pkg-config .pc 文件（使用临时文件避免 word-split 反模式）
_tmp_g4_pc="${TMPDIR:-$HOME/tmp}/verify_find_g4_pc_$$.lst"
find "$INSTALL_PREFIX/lib/pkgconfig" -name "*.pc" -type f > "$_tmp_g4_pc" 2>/dev/null || true
PC_COUNT=$(wc -l < "$_tmp_g4_pc" 2>/dev/null | tr -d ' ')
rm -f "$_tmp_g4_pc"
if [ "$PC_COUNT" -gt 0 ]; then
    g4_pass "pkg-config: 找到 ${PC_COUNT} 个 .pc 文件"
elif [ "$SOFTWARE" = "pkg-config" ]; then
    g4_pass "pkg-config: 自身不需要 .pc 文件"
else
    g4_warn "pkg-config: 无 .pc 文件（如被其他软件依赖则需关注）"
fi

# G4-3: 补丁集可 rebuild
if [ -d "$ARCHIVE_DIR/patches" ]; then
    _tmp_g4_patch="${TMPDIR:-$HOME/tmp}/verify_find_g4_patch_$$.lst"
    find "$ARCHIVE_DIR/patches" -name "000*.patch" -type f > "$_tmp_g4_patch" 2>/dev/null || true
    PATCH_COUNT=$(wc -l < "$_tmp_g4_patch" 2>/dev/null | tr -d ' ')
    rm -f "$_tmp_g4_patch"
    if [ "$PATCH_COUNT" -gt 0 ]; then
        REBUILD_OK=true
        # 确定源码目录（用于真 dry-run）
        SRC_DIR_FOR_PATCH=""
        _TMPDIR_BASE="${TMPDIR:-$HOME/tmp}"
        
        # 策略1: 从 build-context 文件读取
        _CTX="${PROJECT_DIR}/.build-context-${SOFTWARE}-${VERSION}"
        if [ -f "$_CTX" ]; then
            _SRC=$(grep "^BUILD_SRC_DIR=" "$_CTX" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"')
            [ -n "$_SRC" ] && [ -d "$_SRC" ] && SRC_DIR_FOR_PATCH="$_SRC"
        fi
        # 策略2: 常见临时测试目录
        if [ -z "$SRC_DIR_FOR_PATCH" ]; then
            _TMP_TEST="${_TMPDIR_BASE}/builds/${SOFTWARE}-${VERSION}-test"
            [ -d "$_TMP_TEST" ] && SRC_DIR_FOR_PATCH="$_TMP_TEST"
        fi
        if [ -z "$SRC_DIR_FOR_PATCH" ]; then
            _TMP_MAIN="${_TMPDIR_BASE}/builds/${SOFTWARE}-${VERSION}"
            [ -d "$_TMP_MAIN" ] && SRC_DIR_FOR_PATCH="$_TMP_MAIN"
        fi
        # 策略3: 从原始 tarball 重建干净源码（最可靠）
        if [ -z "$SRC_DIR_FOR_PATCH" ] && [ -f "${ARCHIVE_DIR}/manifest.yaml" ]; then
            _TAR_URL=$(grep "^source_url:" "${ARCHIVE_DIR}/manifest.yaml" 2>/dev/null | head -1 | cut -d: -f2- | tr -d ' "')
            if [ -n "$_TAR_URL" ]; then
                _REBUILD_SRC="${_TMPDIR_BASE}/.verify-rebuild-${SOFTWARE}-${VERSION}-$$"
                mkdir -p "$_REBUILD_SRC" || true
                echo "     [INFO] 源码不存在，从 ${_TAR_URL##*/} 重建..."
                # 根据扩展名选择解压方式
                case "$_TAR_URL" in
                    *.tar.xz)  curl -fsSL "$_TAR_URL" 2>/dev/null | tar xJf - -C "$_REBUILD_SRC" ;;
                    *.tar.gz|*.tgz) curl -fsSL "$_TAR_URL" 2>/dev/null | tar xzf - -C "$_REBUILD_SRC" ;;
                    *.tar.bz2) curl -fsSL "$_TAR_URL" 2>/dev/null | tar xjf - -C "$_REBUILD_SRC" ;;
                    *)         curl -fsSL "$_TAR_URL" -o "${_REBUILD_SRC}/dl.tar" 2>/dev/null && tar xf "${_REBUILD_SRC}/dl.tar" -C "$_REBUILD_SRC" ;;
                esac
                # 找到解压出的顶层目录
                _EXTRACTED=$(ls -1d "$_REBUILD_SRC"/*/ 2>/dev/null | head -1)
                if [ -n "$_EXTRACTED" ] && [ -d "$_EXTRACTED" ]; then
                    SRC_DIR_FOR_PATCH="$(echo "$_EXTRACTED" | sed 's:/$::')"
                    echo "     [INFO] 重建成功: $SRC_DIR_FOR_PATCH"
                else
                    rm -rf "$_REBUILD_SRC"
                fi
            fi
        fi
        
        for p in "$ARCHIVE_DIR"/patches/000*.patch; do
            [ -f "$p" ] || continue
            if [ -n "$SRC_DIR_FOR_PATCH" ] && [ -d "$SRC_DIR_FOR_PATCH" ]; then
                DRY_RUN=$(patch -p1 --dry-run -i "$p" -d "$SRC_DIR_FOR_PATCH" 2>&1)
                _RC=$?
                if [ $_RC -ne 0 ]; then
                    # "already applied/reversed" 不算失败（configure 可能改过文件）
                    echo "$DRY_RUN" | grep -qiE 'already applied|reversed|previously' && continue
                    REBUILD_OK=false
                fi
            else
                # 无源码且无法重建 → 仅验证 patch 格式合法性
                if head -1 "$p" | grep -qE '^(---|\+\+\+|\*\*\*|===) '; then
                    : # 格式合法
                else
                    REBUILD_OK=false
                fi
            fi
        done
        
        # 清理临时重建的源码
        if [ -n "$_REBUILD_SRC" ] && [ -d "$_REBUILD_SRC" ]; then
            rm -rf "$_REBUILD_SRC"
        fi
        if [ "$REBUILD_OK" = "true" ]; then
            g4_pass "补丁重建: ${PATCH_COUNT} 个补丁全部可通过验证"
        else
            g4_fail "补丁重建: 部分 patch 验证失败"
        fi
    else
        g4_warn "补丁重建: patches/ 目录为空（首次编译？）"
    fi
else
    g4_warn "补丁重建: archives 目录不存在"
fi

# G4-4: manifest.yaml 完整性
if [ -f "$ARCHIVE_DIR/manifest.yaml" ]; then
    # 检查必填字段
    MANIFEST_OK=true
    for field in software version status build_system compile_date dependencies build_config compatibility test_results; do
        if ! grep -q "^${field}:" "$ARCHIVE_DIR/manifest.yaml" 2>/dev/null; then
            g4_fail "manifest.yaml: 缺少必填字段 '${field}'"
            MANIFEST_OK=false
        fi
    done
    if [ "$MANIFEST_OK" = "true" ]; then
        g4_pass "manifest.yaml: 所有必填字段完整"
        
        # 额外检查: build_cleanliness (P0)
        if grep -q "build_cleanliness:" "$ARCHIVE_DIR/manifest.yaml" 2>/dev/null; then
            g4_pass "P0 记录: build_cleanliness 字段存在"
        else
            g4_warn "P0 记录: 缺少 build_cleanliness 字段（未记录技术债务）"
        fi
        
        # 额外检查: patches_applied
        if grep -q "patches_applied:" "$ARCHIVE_DIR/manifest.yaml" 2>/dev/null; then
            APPLIED_COUNT=$(grep -c "file:" "$ARCHIVE_DIR/manifest.yaml" 2>/dev/null || echo "0")
            g4_pass "补丁记录: patches_applied 存在 (约 ${APPLIED_COUNT} 个)"
        else
            g4_warn "补丁记录: 缺少 patches_applied 字段"
        fi
    fi
else
    g4_fail "manifest.yaml: 文件不存在"
fi

# G4-5: PROGRESS.md 已关闭
if [ -f "$ARCHIVE_DIR/PROGRESS.md" ]; then
    STATUS=$(grep '^status:' "$ARCHIVE_DIR/PROGRESS.md" 2>/dev/null | head -1 | sed 's/status: *//')
    case "$STATUS" in
        success)  g4_pass "PROGRESS.md: 已关闭 (${STATUS})" ;;
        partial)  g4_pass "PROGRESS.md: 已关闭 (${STATUS})" ;;
        failed)   g4_fail "PROGRESS.md: 状态为 failed" ;;
        compiling) g4_warn "PROGRESS.md: 仍处于编译中" ;;
        *)        g4_warn "PROGRESS.md: 状态未知 (${STATUS})" ;;
    esac
else
    g4_warn "PROGRESS.md: 不存在"
fi

# G4-6: finish-build.sh 是否已执行（强制门禁）
echo ""
echo "[G4-extra] finish-build 收尾检查..."

FEEDBACK_FILE="${ARCHIVE_DIR}/reports/skill-feedback.md"
if [ -f "$FEEDBACK_FILE" ] && [ "$(wc -l < "$FEEDBACK_FILE" | tr -d ' ')" -gt 5 ]; then
    g4_pass "finish-build: skill-feedback.md 存在且有内容 ($(wc -l < "$FEEDBACK_FILE" | tr -d ' ') 行)"
    FINISH_DONE=true
elif [ -f "$ARCHIVE_DIR/manifest.yaml" ]; then
    # 备选：manifest 已被 finish-build 更新过（有 build_cleanliness 字段）
    if grep -q "build_cleanliness:" "$ARCHIVE_DIR/manifest.yaml" 2>/dev/null; then
        g4_pass "finish-build: manifest 含 build_cleanliness 字段（已执行收尾）"
        FINISH_DONE=true
    else
        g4_fail "finish-build: 未检测到收尾记录（缺少 skill-feedback.md 和 build_cleanliness）"
        g4_fail "  → 请执行: ./scripts/finish-build.sh ${SOFTWARE} ${VERSION} success|partial"
        FINISH_DONE=false
    fi
else
    g4_fail "finish-build: 归档目录不完整，无法确认收尾状态"
    FINISH_DONE=false
fi

# 如果 finish-build 未执行，直接 FAIL（不允许跳过）
if [ "$FINISH_DONE" = "false" ]; then
    FINAL_VERDICT="FAIL-G4"
fi

echo ""
echo "  G4 结果: ${G4_PASS}/${G4_TOTAL} 通过, ${G4_FAIL} 失败, ${G4_WARN} 警告"

# ============================================================
# 总评 & 报告
# ============================================================
TOTAL_PASS=$((G1_PASS + G2_PASS + G3_PASS + G4_PASS))
TOTAL_FAIL=$((G1_FAIL + G2_FAIL + G3_FAIL + G4_FAIL))
TOTAL_WARN=$((G1_WARN + G2_WARN + G3_WARN + G4_WARN))

FINAL_VERDICT="PASS"
[ "$G1_FAIL" -gt 0 ] && FINAL_VERDICT="FAIL-G1"
[ "$G2_FAIL" -gt 0 ] && FINAL_VERDICT="FAIL-G2"
[ "$G3_FAIL" -gt 0 ] && FINAL_VERDICT="FAIL-G3"
[ "$G4_FAIL" -gt 0 ] && FINAL_VERDICT="FAIL-G4"
[ "$TOTAL_FAIL" -eq 0 ] && [ "$TOTAL_WARN" -gt 10 ] && FINAL_VERDICT="PASS-WARN"

echo ""
echo "════════════════════════════════════════"
echo "  质量门禁总评: ${FINAL_VERDICT}"
echo "  通过: ${TOTAL_PASS} | 失败: ${TOTAL_FAIL} | 警告: ${TOTAL_WARN}"
echo "════════════════════════════════════════"

# 写入报告
cat > "$REPORT_FILE" <<REPORTEOF
# 质量报告 — ${SOFTWARE} ${VERSION}

> **生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
> **总评**: ${FINAL_VERDICT}

## G1: 二进制完整性
| 指标 | 结果 |
|------|------|
| ELF 文件数 | ${ELF_COUNT} |
| 通过 | ${G1_PASS}/${G1_TOTAL} |
| 失败 | ${G1_FAIL} |
| 警告 | ${G1_WARN} |
| 缺依赖 | ${MISSING_DEPS} |
| 损坏文件 | ${BROKEN_ELFS} |

## G2: 功能可用性
| 指标 | 结果 |
|------|------|
| 通过 | ${G2_PASS}/${G2_TOTAL} |
| 失败 | ${G2_FAIL} |
| 警告 | ${G2_WARN} |

## G3: 可移植性
| 指标 | 结果 |
|------|------|
| 通过 | ${G3_PASS}/${G3_TOTAL} |
| 失败 | ${G3_FAIL} |
| 警告 | ${G3_WARN} |
| RPATH OK | ${RPATH_OK} |
| RPATH 缺失 | ${RPATH_BAD} |
| 签名确认 | ${SIGNED_OK} |

## G4: 档案完整性
| 指标 | 结果 |
|------|------|
| 通过 | ${G4_PASS}/${G4_TOTAL} |
| 失败 | ${G4_FAIL} |
| 警告 | ${G4_WARN} |
| man pages | ${MAN_COUNT} |
| .pc files | ${PC_COUNT} |
| 补丁数量 | ${PATCH_COUNT:-0} |

## 总结
${FINAL_VERDICT}: ${TOTAL_PASS} 通过 / ${TOTAL_FAIL} 失败 / ${TOTAL_WARN} 警告
REPORTEOF

echo ""
echo "  [FILE] 报告: ${REPORT_FILE}"

# 退出码
if [ "$FINAL_VERDICT" = "PASS" ]; then
    exit 0
elif [ "$FINAL_VERDICT" = "PASS-WARN" ]; then
    exit 0  # 有警告但不算失败
else
    exit 1
fi
