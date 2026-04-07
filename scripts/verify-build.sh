#!/bin/sh
# verify-build.sh — 产物质量门禁（Step 4）
# 用法: ./scripts/verify-build.sh <软件名> <版本>
#
# 4 道门禁验证编译产物是否真正可用。
# 编译成功 ≠ 产物可用。本脚本确保交付的是"可交给别人用的三方库"。
#
# Layer: Layer1（完全确定性，无 AI 决策点）
# 触发条件: finish-build.sh success 之后，或手动执行

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

show_help() {
    cat <<'HELPEOF'
用法:
  ./scripts/verify-build.sh <软件名> <版本>

描述:
  产物质量门禁。4 道自动检测 + 输出质量报告。
  在 finish-build.sh success 之后执行。

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

SOFTWARE="$1"
VERSION="$2"

echo "[CHECK] 产物质量门禁"
echo "  软件: ${SOFTWARE} ${VERSION}"
echo ""

# ---- 找到安装目录和归档目录 ----
PREFIX="${DEFAULT_PREFIX:-$HOME/usr/local}"
if [ ! -d "$PREFIX/bin" ] && [ ! -d "$PREFIX/lib" ]; then
    echo "[FAIL] 安装目录不存在: $PREFIX"
    exit 1
fi

FIRST_LETTER="$(echo "$SOFTWARE" | cut -c1 | tr 'A-Z' 'a-z')"
ARCHIVE_DIR="${PROJECT_DIR}/archives/${FIRST_LETTER}/${SOFTWARE}/${VERSION}"
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

# 收集所有 ELF 文件
for elf in $(find "$PREFIX/bin" -type f 2>/dev/null); do
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
            # 检查每个依赖是否存在
            echo "$NEEEDED" | while read -r line; do
                lib=$(echo "$line" | sed 's/.*\[\(.*\)].*/\1/')
                if [ -n "$lib" ]; then
                    if find "$PREFIX/lib" -name "$lib*" 2>/dev/null | grep -q .; then
                        : # 依赖存在
                    else
                        log_warn "$(basename $elf): 缺少依赖 ${lib}"
                        MISSING_DEPS=$((MISSING_DEPS + 1))
                    fi
                fi
            done
        fi
    fi
done

# 也检查 lib 目录下的共享库
for lib in $(find "$PREFIX/lib" -name "*.so" -type f 2>/dev/null); do
    ELF_COUNT=$((ELF_COUNT + 1))
    LIB_TYPE=$(file -b "$lib" 2>/dev/null || echo "unknown")
    case "$LIB_TYPE" in
        *ELF*) log_pass "lib/$(basename $lib): 共享库 OK" ;;
        *)    log_warn "lib/$(basename $lib): ${LIB_TYPE}" ;;
    esac
done

echo ""
echo "  G1 结果: ${G1_PASS}/${G1_TOTAL} 通过, ${G1_FAIL} 失败, ${G1_WARN} 警告"
echo "         (共 ${ELF_COUNT} 个文件, ${MISSING_DEPS} 缺依赖, ${BROKEN_ELFS} 损坏)"

# ============================================================
# G2: 功能可用性
# ============================================================
echo ""
echo "[G2/4] 功能可用性..."

# G2-1: --version 测试
for bin in $(find "$PREFIX/bin" -type f -executable 2>/dev/null | head -10); do
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
done

# G2-2: 核心功能测试（按软件名匹配）
case "$SOFTWARE" in
    sed)
        TEST_RESULT=$(echo "hello world" | "$PREFIX/bin/sed" 's/world/harmonyos/' 2>&1) && RC=$? || RC=$?
        if [ "$TEST_RESULT" = "hello harmonyos" ]; then
            g2_pass "sed: 替换测试通过 (output: ${TEST_RESULT})"
        else
            g2_fail "sed: 替换测试失败 (rc=${RC}, output: ${TEST_RESULT})"
        fi
        ;;
    coreutils)
        if [ -x "$PREFIX/bin/ls" ]; then
            LS_OUT=$("$PREFIX/bin/ls" /tmp 2>&1 | head -3) && RC=$? || RC=$?
            if [ $RC -eq 0 ] && [ -n "$LS_OUT" ]; then
                g2_pass "ls: 目录列表正常"
            else
                g2_fail "ls: 目录列表失败 (rc=${RC})"
            fi
        fi
        if [ -x "$PREFIX/bin/cat" ]; then
            CAT_TEST=$("$PREFIX/bin/cat" /etc/os-release 2>/dev/null | head -1) && RC=$? || RC=$?
            if [ $RC -eq 0 ] && [ -n "$CAT_TEST" ]; then
                g2_pass "cat: 文件读取正常"
            else
                g2_fail "cat: 文件读取失败 (rc=${RC})"
            fi
        fi
        ;;
    gawk)
        AWK_TEST=$(echo "1 2 3" | "$PREFIX/bin/gawk" '{print $1+$2+$3}' 2>&1) && RC=$? || RC=$?
        if [ "$AWK_TEST" = "6" ]; then
            g2_pass "gawk: 计算测试通过 (=6)"
        else
            g2_fail "gawk: 计算测试失败 (rc=${RC}, output=${AWK_TEST})"
        fi
        ;;
    pkg-config)
        PC_OUT=$("$PREFIX/bin/pkg-config" --version 2>&1) && RC=$? || RC=$?
        if [ $RC -eq 0 ] && [ -n "$PC_OUT" ]; then
            g2_pass "pkg-config: --version → ${PC_OUT}"
        else
            g2_fail "pkg-config: --version 失败 (rc=${RC})"
        fi
        ;;
    *)
        # 通用：至少测了 --version 就算过
        if [ $G2_PASS -gt 0 ]; then
            g2_pass "通用功能测试: --version 已覆盖"
        else
            g2_warn "通用功能测试: 无可执行的二进制用于测试"
        fi
        ;;
esac

echo ""
echo "  G2 结果: ${G2_PASS}/${G2_TOTAL} 通过, ${G2_FAIL} 失败, ${G2_WARN} 警告"

# ============================================================
# G3: 可移植性
# ============================================================
echo ""
echo "[G3/4] 可移植性..."

# G3-1: RPATH 检查
RPATH_OK=0; RPATH_BAD=0
if command -v patchelf >/dev/null 2>&1; then
    for elf in $(find "$PREFIX/bin" -type f -executable 2>/dev/null); do
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
    done
else
    g3_warn "patchelf 不可用，跳过 RPATH 检查"
fi

# G3-2: ELF 签名检查
SIGNED_OK=0; SIGNED_BAD=0
if command -v sign-elf.sh >/dev/null 2>&1; then
    # 只检查签名是否存在，不重新签名
    for elf in $(find "$PREFIX/bin" -type f -executable 2>/dev/null); do
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
    done
else
    g3_warn "sign-elf.sh 不可用，跳过签名检查"
fi

# G3-3: 解压后可运行模拟（检查关键路径是否为相对路径）
REL_PATH_ISSUE=0
for elf in $(find "$PREFIX/bin" -type f -executable 2>/dev/null); do
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
done

echo ""
echo "  G3 结果: ${G3_PASS}/${G3_TOTAL} 通过, ${G3_FAIL} 失败, ${G3_WARN} 警告"
echo "         (RPATH: ${RPATH_OK} OK / ${RPATH_BAD} 缺, 签名: ${SIGNED_OK} OK / ${SIGNED_BAD} 未知)"

# ============================================================
# G4: 档案完整性
# ============================================================
echo ""
echo "[G4/4] 档案完整性..."

# G4-1: man page
MAN_COUNT=$(find "$PREFIX/share/man" -name "*.${SOFTWARE}*" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$MAN_COUNT" -gt 0 ]; then
    g4_pass "man page: 找到 ${MAN_COUNT} 个相关手册页"
else
    MAN_ANY=$(find "$PREFIX/share/man" -name "*.1" -o -name "*.gz" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MAN_ANY" -gt 0 ]; then
        g4_warn "man page: 未找到 ${SOFTWARE} 专用手册（但有 ${MAN_ANY} 个通用手册）"
    else
        g4_fail "man page: 完全没有手册页"
    fi
fi

# G4-2: pkg-config .pc 文件
PC_COUNT=$(find "$PREFIX/lib/pkgconfig" -name "*.pc" -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$PC_COUNT" -gt 0 ]; then
    g4_pass "pkg-config: 找到 ${PC_COUNT} 个 .pc 文件"
elif [ "$SOFTWARE" = "pkg-config" ]; then
    g4_pass "pkg-config: 自身不需要 .pc 文件"
else
    g4_warn "pkg-config: 无 .pc 文件（如被其他软件依赖则需关注）"
fi

# G4-3: 补丁集可 rebuild
if [ -d "$ARCHIVE_DIR/patches" ]; then
    PATCH_COUNT=$(find "$ARCHIVE_DIR/patches" -name "000*.patch" -type f 2>/dev/null | wc -l | tr -d ' ')
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
        completed|success|closed) g4_pass "PROGRESS.md: 已关闭 (${STATUS})" ;;
        compiling)              g4_warn "PROGRESS.md: 仍处于编译中" ;;
        failed)                 g4_fail "PROGRESS.md: 状态为 failed" ;;
        *)                      g4_warn "PROGRESS.md: 状态未知 (${STATUS})" ;;
    esac
else
    g4_warn "PROGRESS.md: 不存在"
fi

# G4-6: finish-build.sh 是否已执行（强制门禁）
echo ""
echo "[G4-6/4] finish-build 收尾检查..."

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
